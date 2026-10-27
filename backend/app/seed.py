"""Entirely fictional data. Never contacts FPL or changes an existing workspace."""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Fixture, Pick, Player, Snapshot, Workspace

DEMO_KEY = "synthetic-v1"
CLUBS = {
    "NOR": ("Northbridge", "#d55845"),
    "RIV": ("Riverside", "#659cc8"),
    "HAR": ("Harbour City", "#8058b2"),
    "KIN": ("Kingsford", "#c39236"),
    "WES": ("Westhaven", "#418c75"),
    "EAS": ("Eastfield", "#5472b7"),
    "SOU": ("Southbank", "#b85d7d"),
    "MOO": ("Moorland", "#667482"),
}
# name, position, club, price in £0.1m
PLAYERS = [
    ("Ari Vale", "GK", "NOR", 45),
    ("Ben Reed", "GK", "RIV", 40),
    ("Noah Hart", "DEF", "NOR", 55),
    ("Theo Moss", "DEF", "HAR", 50),
    ("Leo Shaw", "DEF", "KIN", 45),
    ("Jack Lane", "DEF", "WES", 40),
    ("Luca Reed", "DEF", "EAS", 40),
    ("Eli Brooks", "MID", "NOR", 95),
    ("Finn Cole", "MID", "HAR", 80),
    ("Kai Bennett", "MID", "RIV", 70),
    ("Owen Hale", "MID", "KIN", 60),
    ("Max Ellis", "MID", "WES", 50),
    ("Sam Rivers", "FWD", "EAS", 80),
    ("Alex Rowan", "FWD", "SOU", 75),
    ("Jude West", "FWD", "MOO", 55),
    ("Oscar Quinn", "GK", "SOU", 50),
    ("Miles Stone", "DEF", "MOO", 48),
    ("Felix Gray", "MID", "EAS", 65),
    ("Evan Birch", "FWD", "HAR", 72),
    ("Robin Ash", "MID", "SOU", 58),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def seed_demo(session: Session) -> None:
    if session.get(Workspace, 1) is None:
        session.add(Workspace(id=1, name="Weekend XI", notes="", updated_at=utc_now()))
    if session.scalar(select(Snapshot).where(Snapshot.source_key == DEMO_KEY)) is not None:
        session.commit()
        return
    snapshot = Snapshot(
        source_key=DEMO_KEY, source="synthetic", season="2026/27", gameweek=10,
        created_at=utc_now(), bank_tenths=12, free_transfers=2,
    )
    session.add(snapshot)
    session.flush()
    players = []
    for index, (name, position, club_code, price) in enumerate(PLAYERS, 1):
        club, color = CLUBS[club_code]
        player = Player(
            snapshot_id=snapshot.id, source_player_id=f"demo-{index}", name=name,
            short_name=name.split()[-1], club=club, club_code=club_code, color=color,
            position=position, price_tenths=price,
        )
        session.add(player)
        players.append(player)
    session.flush()
    # 3-5-2 starting XI, followed by substitute keeper and three outfield subs.
    for slot, index in enumerate([0, 2, 3, 4, 7, 8, 9, 10, 11, 12, 13, 1, 5, 6, 14], 1):
        player = players[index]
        purchase = player.price_tenths - (2 if index in (7, 12) else 0)
        selling = purchase + (player.price_tenths - purchase) // 2
        session.add(Pick(
            snapshot_id=snapshot.id, player_id=player.id, slot=slot,
            is_captain=index == 7, is_vice_captain=index == 12,
            purchase_price_tenths=purchase, selling_price_tenths=selling,
        ))
    for home, away in [("NOR", "HAR"), ("RIV", "KIN"), ("EAS", "WES"), ("SOU", "MOO")]:
        session.add(Fixture(
            snapshot_id=snapshot.id, gameweek=10,
            home_club=CLUBS[home][0], home_code=home,
            away_club=CLUBS[away][0], away_code=away,
        ))
    session.commit()
