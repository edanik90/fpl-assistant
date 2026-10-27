from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Snapshot(Base):
    __tablename__ = "snapshots"
    __table_args__ = (
        CheckConstraint("bank_tenths >= 0"),
        CheckConstraint("free_transfers >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    source_key: Mapped[str] = mapped_column(String(100), unique=True)
    source: Mapped[str] = mapped_column(String(30))
    season: Mapped[str] = mapped_column(String(20))
    gameweek: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40))
    bank_tenths: Mapped[int] = mapped_column(Integer)
    free_transfers: Mapped[int] = mapped_column(Integer)


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "source_player_id"),
        CheckConstraint("price_tenths >= 0"),
        CheckConstraint("position IN ('GK', 'DEF', 'MID', 'FWD')"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    source_player_id: Mapped[str] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(100))
    short_name: Mapped[str] = mapped_column(String(40))
    club: Mapped[str] = mapped_column(String(60))
    club_code: Mapped[str] = mapped_column(String(3))
    color: Mapped[str] = mapped_column(String(7))
    position: Mapped[str] = mapped_column(String(3))
    price_tenths: Mapped[int] = mapped_column(Integer)


class Pick(Base):
    __tablename__ = "picks"
    __table_args__ = (
        UniqueConstraint("snapshot_id", "slot"),
        UniqueConstraint("snapshot_id", "player_id"),
        CheckConstraint("slot BETWEEN 1 AND 15"),
        CheckConstraint("purchase_price_tenths >= 0 AND selling_price_tenths >= 0"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    slot: Mapped[int] = mapped_column(Integer)
    is_captain: Mapped[bool] = mapped_column(Boolean)
    is_vice_captain: Mapped[bool] = mapped_column(Boolean)
    purchase_price_tenths: Mapped[int] = mapped_column(Integer)
    selling_price_tenths: Mapped[int] = mapped_column(Integer)


class Fixture(Base):
    __tablename__ = "fixtures"
    id: Mapped[int] = mapped_column(primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("snapshots.id"))
    gameweek: Mapped[int] = mapped_column(Integer)
    home_club: Mapped[str] = mapped_column(String(60))
    home_code: Mapped[str] = mapped_column(String(3))
    away_club: Mapped[str] = mapped_column(String(60))
    away_code: Mapped[str] = mapped_column(String(3))


class Workspace(Base):
    __tablename__ = "workspace"
    __table_args__ = (CheckConstraint("id = 1"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    notes: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[str] = mapped_column(String(40))
