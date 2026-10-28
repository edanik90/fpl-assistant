"""Local-file ingestion only. No network clients or upstream team operations."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Fixture, Pick, Player, Snapshot
from .seed import utc_now

Identifier = Annotated[int, Field(strict=True, ge=1)]
Money = Annotated[int, Field(strict=True, ge=0, le=10000)]
Week = Annotated[int, Field(strict=True, ge=1, le=60)]


def timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Include a timezone in the capture/kickoff timestamp")
    return parsed.astimezone(timezone.utc).isoformat()


class SourceModel(BaseModel):
    # Retain only supported fields; never store unrelated private account data.
    model_config = ConfigDict(strict=True, extra="ignore", str_strip_whitespace=True)


class Team(SourceModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=60)
    short_name: str = Field(min_length=1, max_length=3)


class Element(SourceModel):
    id: Identifier
    first_name: str = Field(max_length=45)
    second_name: str = Field(min_length=1, max_length=45)
    web_name: str = Field(min_length=1, max_length=40)
    team: Identifier
    element_type: Annotated[int, Field(ge=1, le=4)]
    now_cost: Money


class Bootstrap(SourceModel):
    teams: list[Team] = Field(min_length=2, max_length=100)
    elements: list[Element] = Field(min_length=15, max_length=2000)


class SourceFixture(SourceModel):
    id: Identifier
    event: Week | None = None
    team_h: Identifier
    team_a: Identifier
    kickoff_time: str | None = Field(default=None, max_length=40)

    @field_validator("kickoff_time")
    @classmethod
    def validate_time(cls, value):
        return timestamp(value) if value else value


class SourcePick(SourceModel):
    element: Identifier
    position: Annotated[int, Field(ge=1, le=15)]
    is_captain: bool
    is_vice_captain: bool
    purchase_price: Money | None = None
    selling_price: Money | None = None


class TeamSnapshot(SourceModel):
    picks: list[SourcePick] = Field(min_length=15, max_length=15)


class Match(SourceModel):
    element: Identifier
    fixture: Identifier
    opponent_team: Identifier
    round: Week
    minutes: Annotated[int, Field(ge=0, le=150)]
    total_points: Annotated[int, Field(ge=-100, le=100)]
    # Source JSON uses decimal strings; missing measurements remain absent.
    expected_goals: str | None = Field(default=None, pattern=r"^\d{1,3}(\.\d{1,6})?$")
    expected_assists: str | None = Field(default=None, pattern=r"^\d{1,3}(\.\d{1,6})?$")
    expected_goal_involvements: str | None = Field(default=None, pattern=r"^\d{1,3}(\.\d{1,6})?$")
    expected_goals_conceded: str | None = Field(default=None, pattern=r"^\d{1,3}(\.\d{1,6})?$")
    goals_scored: Annotated[int, Field(ge=0, le=30)] | None = None
    assists: Annotated[int, Field(ge=0, le=30)] | None = None
    clean_sheets: Annotated[int, Field(ge=0, le=1)] | None = None
    goals_conceded: Annotated[int, Field(ge=0, le=30)] | None = None
    saves: Annotated[int, Field(ge=0, le=100)] | None = None
    bonus: Annotated[int, Field(ge=0, le=3)] | None = None
    yellow_cards: Annotated[int, Field(ge=0, le=2)] | None = None
    red_cards: Annotated[int, Field(ge=0, le=1)] | None = None


class PlayerHistory(SourceModel):
    history: list[Match] = Field(max_length=120)


class ImportBundle(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", str_strip_whitespace=True)
    label: str = Field(min_length=1, max_length=80)
    season: str = Field(pattern=r"^20\d{2}/\d{2}$")
    gameweek: Week
    captured_at: str = Field(max_length=40)
    kind: Literal["deadline", "current", "manual"]
    bootstrap: Bootstrap
    fixtures: list[SourceFixture] = Field(max_length=2000)
    team: TeamSnapshot
    player_histories: list[PlayerHistory] = Field(default_factory=list, max_length=2000)
    # Explicit metadata only: entry_history.bank may describe an old deadline,
    # and transfers.limit is not a reliable count of remaining free transfers.
    bank_tenths: Money | None = None
    free_transfers: Annotated[int, Field(ge=0, le=100)] | None = None
    transfer_hits: Annotated[int, Field(ge=0, le=1000)] | None = None
    chip: str | None = Field(default=None, max_length=40)

    @field_validator("captured_at")
    @classmethod
    def validate_capture(cls, value):
        return timestamp(value)

    @field_validator("season")
    @classmethod
    def validate_season(cls, value):
        if (int(value[:4]) + 1) % 100 != int(value[-2:]):
            raise ValueError("Season must contain consecutive years, e.g. 2026/27")
        return value

    @model_validator(mode="after")
    def references(self):
        teams = {t.id for t in self.bootstrap.teams}
        players = {p.id for p in self.bootstrap.elements}
        fixtures = {f.id: f for f in self.fixtures}
        if len(teams) != len(self.bootstrap.teams) or len(players) != len(self.bootstrap.elements) or len(fixtures) != len(self.fixtures):
            raise ValueError("Duplicate team, player or fixture IDs")
        if len({t.short_name.casefold() for t in self.bootstrap.teams}) != len(teams):
            raise ValueError("Team short names must be unique")
        if any(p.team not in teams for p in self.bootstrap.elements):
            raise ValueError("A catalogue player references an unknown team")
        if any(f.team_h not in teams or f.team_a not in teams or f.team_h == f.team_a for f in self.fixtures):
            raise ValueError("A fixture must reference two different known teams")
        if any(p.element not in players for p in self.team.picks):
            raise ValueError("A squad pick references an unknown catalogue player")
        validate_picks([dict(slot=p.position, player_id=p.element, is_captain=p.is_captain, is_vice_captain=p.is_vice_captain) for p in self.team.picks])
        seen = set()
        for history in self.player_histories:
            if len({m.element for m in history.history}) > 1:
                raise ValueError("Each player history file must describe one player")
            for match in history.history:
                fixture = fixtures.get(match.fixture)
                key = (match.element, match.fixture)
                if match.element not in players or not fixture or match.opponent_team not in (fixture.team_h, fixture.team_a) or match.round != fixture.event:
                    raise ValueError("History references an unknown player or inconsistent fixture, opponent or gameweek")
                if key in seen:
                    raise ValueError("Duplicate player/fixture history")
                seen.add(key)
        return self


def validate_picks(picks: list[dict]):
    if len(picks) != 15 or {p["slot"] for p in picks} != set(range(1, 16)) or len({p["player_id"] for p in picks}) != 15:
        raise ValueError("Squad must contain 15 distinct players in slots 1–15")
    if sum(p["is_captain"] for p in picks) != 1 or sum(p["is_vice_captain"] for p in picks) != 1 or any(p["is_captain"] and p["is_vice_captain"] for p in picks):
        raise ValueError("Choose one captain and a different vice-captain")


def import_snapshot(session: Session, payload: ImportBundle) -> tuple[Snapshot, bool]:
    normalized = payload.model_dump(mode="json")
    # A new label is not a new data version. Canonical hashes deduplicate retries.
    content = {k: v for k, v in normalized.items() if k != "label"}
    digest = sha256(json.dumps(content, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    key = f"json:{digest}"
    existing = session.scalar(select(Snapshot).where(Snapshot.source_key == key))
    if existing:
        return existing, False
    snapshot = Snapshot(source_key=key, source="local-json", season=payload.season, gameweek=payload.gameweek,
                        created_at=utc_now(), captured_at=payload.captured_at, label=payload.label, kind=payload.kind,
                        bank_tenths=payload.bank_tenths, free_transfers=payload.free_transfers, import_data=normalized)
    session.add(snapshot)
    session.flush()
    teams = {t.id: t for t in payload.bootstrap.teams}
    players = {}
    for item in payload.bootstrap.elements:
        team = teams[item.team]
        player = Player(snapshot_id=snapshot.id, source_player_id=str(item.id), name=f"{item.first_name} {item.second_name}".strip(),
                        short_name=item.web_name, club=team.name, club_code=team.short_name, color="#42634e",
                        position=("GK", "DEF", "MID", "FWD")[item.element_type - 1], price_tenths=item.now_cost)
        session.add(player)
        players[item.id] = player
    session.flush()
    for item in payload.team.picks:
        session.add(Pick(snapshot_id=snapshot.id, player_id=players[item.element].id, slot=item.position,
                         is_captain=item.is_captain, is_vice_captain=item.is_vice_captain,
                         purchase_price_tenths=item.purchase_price, selling_price_tenths=item.selling_price))
    for item in payload.fixtures:
        home, away = teams[item.team_h], teams[item.team_a]
        session.add(Fixture(snapshot_id=snapshot.id, source_fixture_id=item.id, gameweek=item.event, kickoff_time=item.kickoff_time,
                            home_club=home.name, home_code=home.short_name, away_club=away.name, away_code=away.short_name))
    return snapshot, True
