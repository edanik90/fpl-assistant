from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .config import Settings
from .database import make_engine, migrate
from .models import Fixture, Pick, Player, Snapshot, Workspace
from .schemas import Health, Overview, PlayerRead, Position, WorkspaceRead, WorkspaceUpdate
from .seed import DEMO_KEY, seed_demo, utc_now


def get_session(request: Request):
    with Session(request.app.state.engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def demo_snapshot(session: Session) -> Snapshot:
    snapshot = session.scalar(select(Snapshot).where(Snapshot.source_key == DEMO_KEY))
    if snapshot is None:
        raise HTTPException(status_code=503, detail="Demo data is unavailable. Restart the application.")
    return snapshot


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

    app = FastAPI(title="FPL Assistant", version="0.1.0", lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json", redoc_url=None)

    @app.middleware("http")
    async def local_write_guard(request: Request, call_next):
        # No authentication in this private, loopback-only milestone. Reject browser
        # cross-origin writes even when a request could otherwise bypass CORS.
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse(status_code=403, content={"detail": "Cross-origin writes are not allowed."})
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
        snapshot = demo_snapshot(session)
        return {
            "snapshot": snapshot,
            "workspace": session.get(Workspace, 1),
            "players": session.scalars(select(Player).where(Player.snapshot_id == snapshot.id).order_by(Player.id)).all(),
            "picks": session.scalars(select(Pick).where(Pick.snapshot_id == snapshot.id).order_by(Pick.slot)).all(),
            "fixtures": session.scalars(select(Fixture).where(Fixture.snapshot_id == snapshot.id).order_by(Fixture.id)).all(),
        }

    @app.get("/api/players", response_model=list[PlayerRead])
    def players(session: SessionDep, position: Position | None = None, q: str = Query(default="", max_length=100)):
        snapshot = demo_snapshot(session)
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
