from __future__ import annotations

from fastapi.testclient import TestClient

from conftest import add_holding, seed_trade_case
from src.api import main as api_main


def _client(session, monkeypatch):
    monkeypatch.setattr(api_main, "init_db", lambda: None)

    def override_db():
        yield session

    api_main.app.dependency_overrides[api_main.get_db] = override_db
    return TestClient(api_main.app)


def test_api_health_and_people(session, monkeypatch):
    a, b, mex, bra = seed_trade_case(session)
    client = _client(session, monkeypatch)

    assert client.get("/health").json() == {"status": "ok"}
    people = client.get("/people").json()
    assert [person["name"] for person in people] == ["A", "B"]
    api_main.app.dependency_overrides.clear()


def test_api_dashboard_and_collection(session, monkeypatch):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 2)
    add_holding(session, b, mex, 0)
    client = _client(session, monkeypatch)

    dashboard = client.get("/dashboard").json()
    assert dashboard["stickers_total"] == 2
    assert dashboard["stats"][0]["person_name"] == "A"

    rows = client.get(f"/collection/{a.id}", params={"status": "Doubles"}).json()
    assert rows[0]["display_code"] == "MEX-1"
    api_main.app.dependency_overrides.clear()


def test_api_batch_trade_and_sale(session, monkeypatch):
    a, b, mex, bra = seed_trade_case(session)
    add_holding(session, a, mex, 3)
    add_holding(session, b, mex, 0)
    add_holding(session, a, bra, 0)
    add_holding(session, b, bra, 2)
    client = _client(session, monkeypatch)

    trade_preview = client.post(
        "/trades/preview-batch",
        json={
            "person_a_id": a.id,
            "person_b_id": b.id,
            "raw_codes_from_a": "MEX1",
            "raw_codes_from_b": "BRA1",
        },
    ).json()
    assert trade_preview["can_apply"] is True

    trade_result = client.post(
        "/trades/apply-batch",
        json={"person_a_id": a.id, "person_b_id": b.id, "pairs": trade_preview["pairs"], "actor_name": "Tester"},
    ).json()
    assert trade_result["trade_count"] == 1

    sale_preview = client.post(
        "/sales/preview-batch",
        json={"seller_id": a.id, "buyer_id": b.id, "raw_codes": "MEX1"},
    ).json()
    assert sale_preview["can_apply"] is False
    api_main.app.dependency_overrides.clear()


def test_api_admin_overview(session, monkeypatch):
    seed_trade_case(session)
    client = _client(session, monkeypatch)

    overview = client.get("/admin/overview").json()
    assert overview["overview"]["people_total"] == 2
    assert len(overview["people"]) == 2
    api_main.app.dependency_overrides.clear()
