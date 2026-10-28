from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Position = Literal["GK", "DEF", "MID", "FWD"]


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlayerRead(ReadModel):
    id: int
    source_player_id: str
    name: str
    short_name: str
    club: str
    club_code: str
    color: str
    position: Position
    price_tenths: int


class PickRead(ReadModel):
    slot: int
    player_id: int
    is_captain: bool
    is_vice_captain: bool
    purchase_price_tenths: int | None
    selling_price_tenths: int | None


class FixtureRead(ReadModel):
    id: int
    gameweek: int | None
    source_fixture_id: int | None
    kickoff_time: str | None
    home_club: str
    home_code: str
    away_club: str
    away_code: str


class SnapshotRead(ReadModel):
    id: int
    source: str
    season: str
    gameweek: int
    created_at: str
    bank_tenths: int | None
    free_transfers: int | None
    label: str | None
    captured_at: str | None
    kind: str | None


class WorkspaceRead(ReadModel):
    name: str
    notes: str
    updated_at: str


class WorkspaceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    name: str = Field(min_length=1, max_length=60)
    notes: str = Field(max_length=5000)


class Overview(BaseModel):
    snapshot: SnapshotRead
    workspace: WorkspaceRead
    players: list[PlayerRead]
    picks: list[PickRead]
    fixtures: list[FixtureRead]
    correction_revision: int
    correction_reason: str | None
    transfer_hits: int | None
    chip: str | None
    history_count: int


class Health(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    schema_revision: str


class StrictInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)


class SelectionUpdate(StrictInput):
    snapshot_id: int = Field(ge=1)


class CorrectedPick(StrictInput):
    slot: int = Field(ge=1, le=15)
    player_id: int = Field(ge=1)
    is_captain: bool
    is_vice_captain: bool
    purchase_price_tenths: int | None = Field(ge=0, le=10000)
    selling_price_tenths: int | None = Field(ge=0, le=10000)


class CorrectionValues(StrictInput):
    bank_tenths: int | None = Field(ge=0, le=10000)
    free_transfers: int | None = Field(ge=0, le=100)
    transfer_hits: int | None = Field(ge=0, le=1000)
    chip: str | None = Field(max_length=40)
    picks: list[CorrectedPick] = Field(min_length=15, max_length=15)


class CorrectionUpdate(StrictInput):
    expected_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=500)
    values: CorrectionValues


class CorrectionRead(ReadModel):
    revision: int
    created_at: str
    reason: str
    values: CorrectionValues
