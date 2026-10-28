from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings
from .database import make_engine, migrate
from .models import Correction, Player, Selection, Snapshot, Workspace
from .schemas import (CorrectionRead, CorrectionUpdate, Health, Overview, PlayerRead, Position,
                      SelectionUpdate, SnapshotRead, WorkspaceRead, WorkspaceUpdate)
from .imports import ImportBundle, import_snapshot, validate_picks
from .snapshots import active_snapshot, base_values, find_snapshot, latest_correction, overview_data
from .seed import seed_demo, utc_now


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(settings.database_path)
        app.state.engine = engine
        try:
            migrate(engine)
            with Session(engine) as session:
                seed_demo(session)
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="FPL Assistant", version="0.2.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request, exc):
        # Exclude uploaded input/account data from validation responses.
        errors = [{"loc": e["loc"], "msg": e["msg"]} for e in exc.errors()[:20]]
        return JSONResponse(status_code=422, content={"detail": errors})

    @app.middleware("http")
    async def local_write_guard(request: Request, call_next):
        # No authentication in this private, loopback-only milestone. Reject browser
        # cross-origin writes even when a request could otherwise bypass CORS.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse(status_code=403, content={"detail": "Cross-origin writes are not allowed."})
        if request.method in {"POST", "PUT", "PATCH"} and request.url.path.startswith("/api/"):
            limit = 8 * 1024 * 1024
            chunks, size = [], 0
            async for chunk in request.stream():
                size += len(chunk)
                if size > limit:
                    return JSONResponse(status_code=413, content={"detail": "JSON upload exceeds 8 MiB. Import fewer history files."})
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health", response_model=Health)
    def health(session: SessionDep):
        try:
            revision = session.scalar(text("SELECT version_num FROM alembic_version"))
            workspace = session.get(Workspace, 1)
            if revision is None or workspace is None:
                raise HTTPException(status_code=503, detail="Database is not initialized.")
        except SQLAlchemyError:
            raise HTTPException(status_code=503, detail="Database is unavailable.") from None
        return Health(status="ok", database="ok", schema_revision=revision)

    @app.get("/api/overview", response_model=Overview)
    def overview(session: SessionDep):
        return overview_data(session, active_snapshot(session))

    @app.get("/api/snapshots", response_model=list[SnapshotRead])
    def snapshots(session: SessionDep):
        return session.scalars(select(Snapshot).order_by(Snapshot.id.desc())).all()

    @app.put("/api/selection", response_model=Overview)
    def select_snapshot(payload: SelectionUpdate, session: SessionDep):
        snapshot = find_snapshot(session, payload.snapshot_id)
        session.merge(Selection(id=1, snapshot_id=snapshot.id))
        session.commit()
        return overview_data(session, snapshot)

    @app.post("/api/imports", response_model=Overview)
    def import_files(payload: ImportBundle, session: SessionDep):
        try:
            snapshot, _created = import_snapshot(session, payload)
            session.merge(Selection(id=1, snapshot_id=snapshot.id))
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Another import completed concurrently. Retry this import.") from None
        return overview_data(session, snapshot)

    @app.get("/api/snapshots/{snapshot_id}/original")
    def original(snapshot_id: int, session: SessionDep):
        snapshot = find_snapshot(session, snapshot_id)
        return {"snapshot": SnapshotRead.model_validate(snapshot), "values": base_values(session, snapshot), "import_data": snapshot.import_data}

    @app.get("/api/snapshots/{snapshot_id}/corrections", response_model=list[CorrectionRead])
    def corrections(snapshot_id: int, session: SessionDep):
        find_snapshot(session, snapshot_id)
        return session.scalars(select(Correction).where(Correction.snapshot_id == snapshot_id).order_by(Correction.revision.desc())).all()

    @app.post("/api/snapshots/{snapshot_id}/corrections", response_model=Overview)
    def correct(snapshot_id: int, payload: CorrectionUpdate, session: SessionDep):
        snapshot = find_snapshot(session, snapshot_id)
        latest = latest_correction(session, snapshot_id)
        revision = latest.revision if latest else 0
        if payload.expected_revision != revision:
            raise HTTPException(status_code=409, detail="Corrections changed in another tab. Reload before editing again.")
        values = payload.values.model_dump()
        try:
            validate_picks(values["picks"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        allowed = set(session.scalars(select(Player.id).where(Player.snapshot_id == snapshot_id)))
        if any(p["player_id"] not in allowed for p in values["picks"]):
            raise HTTPException(status_code=422, detail="Every corrected player must belong to this snapshot's catalogue.")
        session.add(Correction(snapshot_id=snapshot_id, revision=revision + 1, created_at=utc_now(), reason=payload.reason, values=values))
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise HTTPException(status_code=409, detail="Corrections changed concurrently. Reload before editing again.") from None
        return overview_data(session, snapshot)

    @app.get("/api/players", response_model=list[PlayerRead])
    def players(session: SessionDep, position: Position | None = None, q: str = Query(default="", max_length=100)):
        snapshot = active_snapshot(session)
        statement = select(Player).where(Player.snapshot_id == snapshot.id).order_by(Player.name)
        if position:
            statement = statement.where(Player.position == position)
        query = q.strip().casefold()
        return [p for p in session.scalars(statement) if query in f"{p.name} {p.club}".casefold()]

    @app.put("/api/workspace", response_model=WorkspaceRead)
    def update_workspace(payload: WorkspaceUpdate, session: SessionDep):
        workspace = session.get(Workspace, 1)
        if workspace is None:
            raise HTTPException(status_code=503, detail="Workspace is not initialized.")
        workspace.name, workspace.notes = payload.name, payload.notes
        workspace.updated_at = utc_now()
        session.commit()
        session.refresh(workspace)
        return workspace

    # Reserve unknown API paths before the static mount, so they cannot return HTML.
    @app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def missing_api(path: str):
        raise HTTPException(status_code=404, detail="API endpoint not found.")

    if settings.static_dir.is_dir():
        app.mount("/", StaticFiles(directory=settings.static_dir, html=True), name="frontend")
    return app


app = create_app()
