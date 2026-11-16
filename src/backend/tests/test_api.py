import pytest
from fastapi.testclient import TestClient

from app import mock_db
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _reset():
    mock_db.reset()


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_rooms():
    r = client.get("/api/v1/rooms")
    assert r.status_code == 200
    assert len(r.json()) == 8


def test_list_rooms_filters():
    occupied = client.get("/api/v1/rooms", params={"occupied": True}).json()
    assert occupied and all(x["occupied"] for x in occupied)
    found = client.get("/api/v1/rooms", params={"q": "bibli"}).json()
    assert [x["id"] for x in found] == [203]


def test_get_room_404():
    assert client.get("/api/v1/rooms/999").status_code == 404


def test_energy_saving_analytics():
    r = client.get("/api/v1/rooms/analytics/energy-saving")
    assert r.status_code == 200
    body = r.json()
    assert body["total_rooms_monitored"] == 8
    assert body["rooms_with_ac_on"] == 6
    assert body["idle_rooms_with_ac_on"] == 2
    assert body["estimated_kwh_saved_today"] > 0
    assert "status_rule" in body


def test_critical_alerts_summary():
    r = client.get("/api/v1/alerts/critical/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["total_critical_alerts"] == 3
    assert body["action_required"] is True
    assert len(body["alerts"]) == 3
    assert all(a["level"] == "high" for a in body["alerts"])


def test_list_alerts_and_filter():
    assert len(client.get("/api/v1/alerts").json()) == 7
    high = client.get("/api/v1/alerts", params={"level": "high"}).json()
    assert len(high) == 3 and all(a["level"] == "high" for a in high)
    assert client.get("/api/v1/alerts", params={"level": "xyz"}).status_code == 422


def test_cut_ac_success_resolves_alert():
    r = client.post("/api/v1/rooms/102/ac/cut")
    assert r.status_code == 200
    body = r.json()
    assert body["success"] and body["room"]["ac"] is False
    assert body["resolved_alerts"] == 1
    assert client.get("/api/v1/alerts", params={"room_id": 102}).json() == []


def test_cut_ac_twice_conflict():
    client.post("/api/v1/rooms/102/ac/cut")
    assert client.post("/api/v1/rooms/102/ac/cut").status_code == 409


def test_cut_ac_not_found():
    assert client.post("/api/v1/rooms/999/ac/cut").status_code == 404


def test_cut_ac_simulated_error():
    assert client.post("/api/v1/rooms/102/ac/cut", params={"simulate_error": True}).status_code == 503
    assert client.get("/api/v1/rooms/102").json()["ac"] is True


def test_database_integration_routes():
    # Testa rota de status da conexão
    status_res = client.get("/api/v1/database/status")
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["status"] == "connected"
    assert "dialect" in status_data

    # Simula gravação de telemetria
    mock_db.update_room_telemetry(room_id=101, occupied=True, potencia_w=1.5, corrente_ma=300)
    telemetrias = client.get("/api/v1/database/telemetrias", params={"sala_id": 101}).json()
    assert len(telemetrias) >= 1
    assert telemetrias[0]["sala_id"] == 101
    assert telemetrias[0]["ocupado"] is True

    # Realiza um corte de ar-condicionado e verifica registro na tabela avisos_oled
    client.post("/api/v1/rooms/105/ac/cut")
    avisos = client.get("/api/v1/database/avisos-oled", params={"sala_id": 105}).json()
    assert len(avisos) >= 1
    assert avisos[0]["sala_id"] == 105
    assert "CORTE" in avisos[0]["mensagem"].upper()
