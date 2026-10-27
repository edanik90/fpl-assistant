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
    purchase_price_tenths: int
    selling_price_tenths: int


class FixtureRead(ReadModel):
    id: int
    gameweek: int
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
    bank_tenths: int
    free_transfers: int


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


class Health(BaseModel):
    status: Literal["ok"]
    database: Literal["ok"]
    schema_revision: str
