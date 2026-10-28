from copy import deepcopy
import json
from pathlib import Path
import socket

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, text

from app.config import Settings
from app.database import make_engine, migrate
from app.main import create_app


@pytest.fixture
def settings(tmp_path):
    return Settings(data_dir=tmp_path / "data", static_dir=tmp_path / "static")


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client


@pytest.fixture
def bundle():
    path = Path("examples/snapshot.json")
    if not path.exists():
        path = Path(__file__).resolve().parents[2] / "frontend/public/examples/snapshot.json"
    return json.loads(path.read_text())


def imported(client, bundle):
    result = client.post("/api/imports", json=bundle)
    assert result.status_code == 200, result.text
    return result.json()


def correction(data, reason="Confirmed actual squad"):
    return {"expected_revision": data["correction_revision"], "reason": reason, "values": {
        "bank_tenths": data["snapshot"]["bank_tenths"], "free_transfers": data["snapshot"]["free_transfers"],
        "transfer_hits": data["transfer_hits"], "chip": data["chip"], "picks": deepcopy(data["picks"]),
    }}


def test_import_unknowns_source_ids_and_deduplication(client, bundle):
    demo = client.get("/api/overview").json()
    bundle["team"]["email"] = "private@example.invalid"
    bundle["team"]["transfers"] = {"bank": 12, "limit": 99}
    data = imported(client, bundle)
    assert data["snapshot"]["source"] == "local-json"
    assert data["snapshot"]["bank_tenths"] is None
    assert data["snapshot"]["free_transfers"] is None
    assert data["transfer_hits"] is None and data["chip"] is None
    assert all(p["selling_price_tenths"] is None and p["purchase_price_tenths"] is None for p in data["picks"])
    assert data["history_count"] == 1
    assert data["snapshot"]["captured_at"] == "2026-10-27T12:00:00+00:00"
    assert {p["source_player_id"] for p in data["players"]} == set(map(str, range(1, 21)))
    original = client.get(f'/api/snapshots/{data["snapshot"]["id"]}/original').json()
    assert "email" not in original["import_data"]["team"]
    assert "transfers" not in original["import_data"]["team"]
    assert original["import_data"]["player_histories"][0]["history"][0]["expected_assists"] is None
    bundle["label"] = "Retry label"
    assert imported(client, bundle)["snapshot"]["id"] == data["snapshot"]["id"]
    assert len(client.get("/api/snapshots").json()) == 2
    restored = client.put("/api/selection", json={"snapshot_id": demo["snapshot"]["id"]}).json()
    assert restored == demo


@pytest.mark.parametrize("damage", [
    lambda b: b["bootstrap"]["elements"][0].update(now_cost=4.5),
    lambda b: b["bootstrap"]["elements"][0].update(now_cost=True),
    lambda b: b["bootstrap"]["elements"][0].update(now_cost=-1),
    lambda b: b["bootstrap"]["elements"].append(b["bootstrap"]["elements"][0]),
    lambda b: b["bootstrap"]["elements"][0].update(team=999),
    lambda b: b["team"]["picks"][0].update(element=999),
    lambda b: b["team"]["picks"][0].update(position=2),
    lambda b: b["team"]["picks"][0].update(element=b["team"]["picks"][1]["element"]),
    lambda b: b["team"]["picks"][0].update(is_captain=True),
    lambda b: b["fixtures"][0].update(team_a=999),
    lambda b: b["player_histories"][0]["history"][0].update(fixture=999),
    lambda b: b["player_histories"][0]["history"][0].update(expected_goals="NaN"),
    lambda b: b.update(season="2026/28"),
    lambda b: b.update(captured_at="2026-10-27T12:00:00"),
    lambda b: b.update(bank_tenths="12"),
])
def test_invalid_import_is_atomic(client, bundle, damage):
    before = client.get("/api/overview").json()
    damage(bundle)
    result = client.post("/api/imports", json=bundle)
    assert result.status_code == 422, result.text
    assert client.get("/api/overview").json() == before
    assert len(client.get("/api/snapshots").json()) == 1


def test_corrections_are_separate_versioned_and_snapshot_scoped(client, bundle):
    data = imported(client, bundle)
    snapshot_id = data["snapshot"]["id"]
    original = client.get(f"/api/snapshots/{snapshot_id}/original").json()
    payload = correction(data)
    payload["values"].update(bank_tenths=0, free_transfers=0, transfer_hits=4, chip="none")
    payload["values"]["picks"][0].update(player_id=data["players"][15]["id"], purchase_price_tenths=48, selling_price_tenths=49)
    updated = client.post(f"/api/snapshots/{snapshot_id}/corrections", json=payload)
    assert updated.status_code == 200, updated.text
    saved = updated.json()
    assert saved["correction_revision"] == 1
    assert saved["snapshot"]["bank_tenths"] == 0 and saved["snapshot"]["free_transfers"] == 0
    assert saved["picks"][0]["selling_price_tenths"] == 49
    assert client.get(f"/api/snapshots/{snapshot_id}/original").json() == original
    assert client.post(f"/api/snapshots/{snapshot_id}/corrections", json=payload).status_code == 409
    assert len(client.get(f"/api/snapshots/{snapshot_id}/corrections").json()) == 1
    bundle["captured_at"] = "2026-10-28T12:00:00Z"
    fresh = imported(client, bundle)
    assert fresh["correction_revision"] == 0 and fresh["snapshot"]["bank_tenths"] is None
    assert fresh["players"][0]["id"] != saved["players"][0]["id"]
    foreign = correction(fresh)
    foreign["values"]["picks"][0]["player_id"] = saved["players"][0]["id"]
    assert client.post(f'/api/snapshots/{fresh["snapshot"]["id"]}/corrections', json=foreign).status_code == 422
    assert client.put("/api/selection", json={"snapshot_id": snapshot_id}).json() == saved
    reset = correction(saved, "Restore original snapshot")
    reset["values"] = original["values"]
    reverted = client.post(f"/api/snapshots/{snapshot_id}/corrections", json=reset).json()
    assert reverted["correction_revision"] == 2
    assert reverted["snapshot"]["bank_tenths"] is None
    assert len(client.get(f"/api/snapshots/{snapshot_id}/corrections").json()) == 2


@pytest.mark.parametrize("field,value", [("bank_tenths", -1), ("bank_tenths", 1.5), ("bank_tenths", True), ("free_transfers", -1)])
def test_invalid_correction_does_not_overwrite(client, bundle, field, value):
    data = imported(client, bundle)
    payload = correction(data)
    payload["values"][field] = value
    assert client.post(f'/api/snapshots/{data["snapshot"]["id"]}/corrections', json=payload).status_code == 422
    assert client.get("/api/overview").json() == data


def test_import_and_corrections_persist_offline(settings, bundle, monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Imports must work offline")
    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    with TestClient(create_app(settings)) as first:
        first.put("/api/workspace", json={"name": "Keep me", "notes": "Do not overwrite"})
        data = imported(first, bundle)
        payload = correction(data)
        payload["values"]["bank_tenths"] = 17
        saved = first.post(f'/api/snapshots/{data["snapshot"]["id"]}/corrections', json=payload).json()
    with TestClient(create_app(settings)) as second:
        assert second.get("/api/overview").json() == saved
        assert saved["workspace"]["notes"] == "Do not overwrite"
        assert {p["id"] for p in second.get("/api/players").json()} == {p["id"] for p in saved["players"]}


def test_size_limit_malformed_json_and_origin_guard(client, bundle):
    before = client.get("/api/overview").json()
    assert client.post("/api/imports", content=b" " * (8 * 1024 * 1024 + 1), headers={"Content-Type": "application/json"}).status_code == 413
    assert client.post("/api/imports", content=b"{bad", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.post("/api/imports", json=bundle, headers={"Origin": "https://foreign.invalid"}).status_code == 403
    assert client.put("/api/selection", json={"snapshot_id": 999}).status_code == 404
    assert client.get("/api/overview").json() == before


def test_existing_milestone1_database_upgrade_preserves_rows(settings):
    engine = make_engine(settings.database_path)
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    with engine.begin() as conn:
        config.attributes["connection"] = conn
        command.upgrade(config, "0001_initial")
        conn.execute(text("INSERT INTO snapshots VALUES (1, 'old', 'synthetic', '2026/27', 10, '2026-10-27T00:00:00+00:00', 12, 2)"))
        conn.execute(text("INSERT INTO players VALUES (1, 1, 'p1', 'Old player', 'Old', 'Old club', 'OLD', '#42634e', 'GK', 45)"))
        conn.execute(text("INSERT INTO picks VALUES (1, 1, 1, 1, 1, 0, 43, 44)"))
        conn.execute(text("INSERT INTO workspace VALUES (1, 'Saved name', 'Saved notes', '2026-10-27T00:00:00+00:00')"))
    migrate(engine)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT notes FROM workspace")) == "Saved notes"
        assert conn.scalar(text("SELECT selling_price_tenths FROM picks")) == 44
        assert conn.scalar(text("SELECT bank_tenths FROM snapshots")) == 12
        assert not conn.exec_driver_sql("PRAGMA foreign_key_check").all()
        assert conn.scalar(text("PRAGMA foreign_keys")) == 1
        assert len(inspect(conn).get_check_constraints("snapshots")) == 2
        assert len(inspect(conn).get_check_constraints("picks")) == 2
    engine.dispose()


def test_confirmed_zero_values_ownership_prices_and_unscheduled_fixture(client, bundle):
    bundle.update(bank_tenths=0, free_transfers=0, transfer_hits=0, chip="none")
    bundle["team"]["picks"][0].update(purchase_price=43, selling_price=44)
    bundle["fixtures"].append({"id": 99, "event": None, "team_h": 1, "team_a": 2, "kickoff_time": None})
    data = imported(client, bundle)
    assert data["snapshot"]["bank_tenths"] == 0
    assert data["snapshot"]["free_transfers"] == 0
    assert data["transfer_hits"] == 0 and data["chip"] == "none"
    assert data["picks"][0]["purchase_price_tenths"] == 43
    assert data["picks"][0]["selling_price_tenths"] == 44
    assert data["fixtures"][-1]["gameweek"] is None
    assert data["fixtures"][-1]["source_fixture_id"] == 99


def test_failed_upgrade_rolls_back_schema_and_revision(settings):
    engine = make_engine(settings.database_path)
    config = Config()
    config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        conn.commit()
        with conn.begin():
            config.attributes["connection"] = conn
            command.upgrade(config, "0001_initial")
            # Deliberately corrupt a pre-upgrade DB to exercise failure recovery.
            conn.execute(text("INSERT INTO players VALUES (1, 999, 'p1', 'Old', 'Old', 'Club', 'OLD', '#42634e', 'GK', 45)"))
    with pytest.raises(RuntimeError, match="Foreign key validation failed"):
        migrate(engine)
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT version_num FROM alembic_version")) == "0001_initial"
        assert "label" not in {c["name"] for c in inspect(conn).get_columns("snapshots")}
        assert not any(t.startswith("_alembic_tmp_") for t in inspect(conn).get_table_names())
        assert conn.scalar(text("SELECT name FROM players")) == "Old"
        assert conn.scalar(text("PRAGMA foreign_keys")) == 1
    engine.dispose()
