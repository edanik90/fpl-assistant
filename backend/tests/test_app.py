from collections import Counter
import socket

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import text

from app.config import Settings
from app.database import Base, make_engine, migrate
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", static_dir=tmp_path / "static")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


def test_migrations_are_repeatable_and_match_models(settings):
    engine = make_engine(settings.database_path)
    try:
        migrate(engine)
        migrate(engine)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001_initial"
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        engine.dispose()


def test_health_and_demo_integrity(client):
    assert client.get("/api/health").json() == {"status": "ok", "database": "ok", "schema_revision": "0001_initial"}
    data = client.get("/api/overview").json()
    assert data["snapshot"]["source"] == "synthetic"
    assert data["snapshot"]["created_at"].endswith("+00:00")
    assert len(data["players"]) == 20
    assert len(data["fixtures"]) == 4
    picks = data["picks"]
    assert [p["slot"] for p in picks] == list(range(1, 16))
    assert len({p["player_id"] for p in picks}) == 15
    assert sum(p["is_captain"] for p in picks) == 1
    assert sum(p["is_vice_captain"] for p in picks) == 1
    players = {p["id"]: p for p in data["players"]}
    counts = Counter(players[p["player_id"]]["position"] for p in picks)
    assert counts == {"GK": 2, "DEF": 5, "MID": 5, "FWD": 3}
    assert max(Counter(players[p["player_id"]]["club_code"] for p in picks).values()) <= 3
    assert Counter(players[p["player_id"]]["position"] for p in picks[:11]) == {"GK": 1, "DEF": 3, "MID": 5, "FWD": 2}
    for pick in picks:
        current = players[pick["player_id"]]["price_tenths"]
        assert type(current) is int
        assert pick["selling_price_tenths"] <= current
    # These are fixed synthetic examples, not a general implementation of season rules.
    assert any(p["selling_price_tenths"] < players[p["player_id"]]["price_tenths"] for p in picks)


def test_workspace_survives_new_app_and_seed_does_not_overwrite(settings):
    with TestClient(create_app(settings)) as first:
        before = first.get("/api/overview").json()
        response = first.put("/api/workspace", json={"name": "My saved XI", "notes": "Watch the minutes.\nKeep a transfer."})
        assert response.status_code == 200
        saved = response.json()
    with TestClient(create_app(settings)) as second:
        after = second.get("/api/overview").json()
        assert after["workspace"] == saved
        for key in ("snapshot", "players", "picks", "fixtures"):
            assert after[key] == before[key]


@pytest.mark.parametrize("payload", [
    {"name": "   ", "notes": ""},
    {"name": "x" * 61, "notes": ""},
    {"name": "Name", "notes": "x" * 5001},
    {"name": 123, "notes": ""},
    {"name": "Name", "notes": "", "bank_tenths": -5},
    {"name": "Name"},
])
def test_invalid_workspace_does_not_change_database(client, payload):
    before = client.get("/api/overview").json()["workspace"]
    assert client.put("/api/workspace", json=payload).status_code == 422
    assert client.get("/api/overview").json()["workspace"] == before


def test_player_search_and_filters(client):
    assert len(client.get("/api/players?position=GK").json()) == 3
    result = client.get("/api/players", params={"q": "  BROOKS  ", "position": "MID"}).json()
    assert [p["name"] for p in result] == ["Eli Brooks"]
    assert client.get("/api/players?q=missing").json() == []
    assert client.get("/api/players?position=INVALID").status_code == 422


def test_unknown_api_is_json_and_snapshot_is_read_only(client):
    response = client.get("/api/not-found")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    assert client.post("/api/overview", json={}).status_code in (404, 405)
    assert client.get("/api/overview").headers["cache-control"] == "no-store"


def test_cross_origin_write_is_rejected(client):
    payload = {"name": "A workspace", "notes": "A note"}
    before = client.get("/api/overview").json()["workspace"]
    assert client.put("/api/workspace", json=payload, headers={"Origin": "https://unrelated.example"}).status_code == 403
    assert client.get("/api/overview").json()["workspace"] == before
    assert client.put("/api/workspace", json=payload, headers={"Origin": "http://testserver"}).status_code == 200


def test_health_fails_when_database_schema_is_unavailable(client):
    with client.app.state.engine.begin() as connection:
        connection.execute(text("DROP TABLE workspace"))
    assert client.get("/api/health").status_code == 503


def test_static_frontend_served_without_masking_missing_assets(settings):
    settings.static_dir.mkdir()
    (settings.static_dir / "index.html").write_text("<html>FPL Assistant</html>")
    with TestClient(create_app(settings)) as client:
        assert client.get("/").status_code == 200
        assert "FPL Assistant" in client.get("/").text
        assert client.get("/missing.js").status_code == 404
        assert client.get("/api/missing").status_code == 404


def test_demo_needs_no_external_network(settings, monkeypatch):
    def block_network(*args, **kwargs):
        raise AssertionError("The demo must not contact external services")
    monkeypatch.setattr(socket, "create_connection", block_network)
    monkeypatch.setattr(socket, "getaddrinfo", block_network)
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/overview").status_code == 200
        assert client.put("/api/workspace", json={"name": "Offline", "notes": "Saved offline"}).status_code == 200
