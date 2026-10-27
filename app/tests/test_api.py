from fastapi.testclient import TestClient

from main import app


def test_health():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_with_database():
    with TestClient(app) as client:
        assert client.get("/ready").status_code == 200


def test_create_event_then_stats():
    with TestClient(app) as client:
        created = client.post("/events", json={"type": "test", "payload": {"k": 1}})
        stats = client.get("/events/stats").json()
    assert created.status_code == 201
    assert any(s["type"] == "test" and s["total"] >= 1 for s in stats)


def test_event_without_type_is_rejected():
    with TestClient(app) as client:
        response = client.post("/events", json={"payload": {}})
    assert response.status_code == 422
