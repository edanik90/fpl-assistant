from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Correction, Fixture, Pick, Player, Selection, Snapshot, Workspace
from .schemas import PickRead, SnapshotRead
from .seed import DEMO_KEY


def find_snapshot(session: Session, snapshot_id: int) -> Snapshot:
    snapshot = session.get(Snapshot, snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return snapshot


def active_snapshot(session: Session) -> Snapshot:
    selection = session.get(Selection, 1)
    if selection:
        return find_snapshot(session, selection.snapshot_id)
    demo = session.scalar(select(Snapshot).where(Snapshot.source_key == DEMO_KEY))
    if demo is None:
        raise HTTPException(status_code=503, detail="Snapshot unavailable. Restart the application.")
    return demo


def latest_correction(session: Session, snapshot_id: int) -> Correction | None:
    return session.scalar(select(Correction).where(Correction.snapshot_id == snapshot_id).order_by(Correction.revision.desc()).limit(1))


def base_values(session: Session, snapshot: Snapshot) -> dict:
    imported = snapshot.import_data or {}
    picks = session.scalars(select(Pick).where(Pick.snapshot_id == snapshot.id).order_by(Pick.slot)).all()
    return dict(bank_tenths=snapshot.bank_tenths, free_transfers=snapshot.free_transfers,
                transfer_hits=imported.get("transfer_hits"), chip=imported.get("chip"),
                picks=[PickRead.model_validate(p).model_dump() for p in picks])


def overview_data(session: Session, snapshot: Snapshot) -> dict:
    correction = latest_correction(session, snapshot.id)
    values = correction.values if correction else base_values(session, snapshot)
    summary = SnapshotRead.model_validate(snapshot).model_dump()
    summary.update(bank_tenths=values["bank_tenths"], free_transfers=values["free_transfers"])
    return dict(snapshot=summary, workspace=session.get(Workspace, 1),
                players=session.scalars(select(Player).where(Player.snapshot_id == snapshot.id).order_by(Player.id)).all(),
                picks=sorted(values["picks"], key=lambda p: p["slot"]),
                fixtures=session.scalars(select(Fixture).where(Fixture.snapshot_id == snapshot.id).order_by(Fixture.id)).all(),
                correction_revision=correction.revision if correction else 0,
                correction_reason=correction.reason if correction else None,
                transfer_hits=values["transfer_hits"], chip=values["chip"],
                history_count=sum(len(h["history"]) for h in (snapshot.import_data or {}).get("player_histories", [])))
