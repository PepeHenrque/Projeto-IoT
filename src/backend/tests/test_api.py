import os
import tempfile

# Antes de importar a aplicação: banco SQLite temporário (não mexe no MySQL de ninguém) e sem conexão real ao broker.
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tempfile.mkdtemp(), "teste.db")
os.environ["CAMPUS_DISABLE_MQTT"] = "1"

import pytest
from fastapi.testclient import TestClient

from app import device, mock_db
from app.main import TOPICO_COMANDOS, TOPICO_STATUS, TOPICO_TELEMETRIA, app, handle_mqtt_message

client = TestClient(app)
client.__enter__()          # executa o lifespan (cria as tabelas e a carga inicial)

FORM = {"Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"}   # mesmo formato que o front envia


@pytest.fixture(autouse=True)
def _reset():
    mock_db.reset()
    device.reset()


def esp_envia(**campos):
    """Simula o ESP32 publicando telemetria no broker."""
    payload = {"sala_id": "SALA_101", "ocupado": True, "modo": "AUTO", "ac_ligado": True,
               "carga_ligada": True, "potencia_w": 1100.0, "corrente_ma": 5000}
    payload.update(campos)
    import json
    handle_mqtt_message(TOPICO_TELEMETRIA, json.dumps(payload).encode())


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_list_rooms_somente_sala_101():
    r = client.get("/api/v1/rooms")
    assert r.status_code == 200
    assert [x["id"] for x in r.json()] == [101]


def test_list_rooms_filters():
    assert [x["id"] for x in client.get("/api/v1/rooms", params={"q": "101"}).json()] == [101]
    assert client.get("/api/v1/rooms", params={"q": "bibli"}).json() == []


def test_outras_salas_nao_existem():
    assert client.get("/api/v1/rooms/102").status_code == 404
    assert client.get("/api/v1/rooms/999").status_code == 404
    assert client.post("/api/v1/rooms/102/ac/cut").status_code == 404


def test_sala_101_segue_a_telemetria():
    esp_envia(ocupado=True, ac_ligado=True, carga_ligada=True)
    sala = client.get("/api/v1/rooms/101").json()
    assert sala["occupied"] is True and sala["ac"] is True
    esp_envia(ocupado=False, modo="OFF", carga_ligada=False)
    sala = client.get("/api/v1/rooms/101").json()
    assert sala["occupied"] is False and sala["ac"] is False


def test_energy_saving_analytics():
    esp_envia(ocupado=False, modo="ON", ac_ligado=True, carga_ligada=True)
    body = client.get("/api/v1/rooms/analytics/energy-saving").json()
    assert body["total_rooms_monitored"] == 1
    assert body["rooms_with_ac_on"] == 1
    assert body["idle_rooms_with_ac_on"] == 1
    assert "status_rule" in body


def test_alerts_sem_dados_falsos():
    assert client.get("/api/v1/alerts").json() == []
    body = client.get("/api/v1/alerts/critical/summary").json()
    assert body["total_critical_alerts"] == 0 and body["action_required"] is False
    assert client.get("/api/v1/alerts", params={"level": "xyz"}).status_code == 422


def test_cut_ac_simulated_error():
    esp_envia()
    assert client.post("/api/v1/rooms/101/ac/cut", params={"simulate_error": True}).status_code == 503
    assert device.desired()["ac"] == "ON"


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
    esp_envia()   # a Sala 101 só aceita comando com o ESP32 online
    assert client.post("/api/v1/rooms/101/ac/cut").status_code == 200
    avisos = client.get("/api/v1/database/avisos-oled", params={"sala_id": 101}).json()
    assert len(avisos) >= 1
    assert avisos[0]["sala_id"] == 101
    assert "CORTE" in avisos[0]["mensagem"].upper()


# ------------------------------------------------------------ integração front-end <-> ESP32
def test_telemetria_offline_sem_esp32():
    r = client.get("/api/v1/telemetria")
    assert r.status_code == 503
    assert "offline" in r.json()["erro"]


def test_telemetria_reflete_esp32():
    esp_envia(ocupado=False, modo="ON", potencia_w=1100.0)
    t = client.get("/api/v1/telemetria").json()
    assert t["ocupada"] is False
    assert t["potencia_w"] == 1100.0
    assert t["carga"] == {"modo": "ON", "ligada": True}
    assert t["ac"] == {"ligado": True}


def test_status_offline_do_lwt_derruba_telemetria():
    esp_envia()
    handle_mqtt_message(TOPICO_STATUS, b"offline")
    assert client.get("/api/v1/telemetria").status_code == 503


def test_comando_carga_formulario():
    esp_envia()
    r = client.post("/api/v1/comando-carga", content="comando=OFF", headers=FORM)
    assert r.status_code == 200
    assert r.json()["carga"] == {"modo": "OFF", "ligada": False}
    assert device.desired()["modo_carga"] == "OFF"
    # e dá para voltar ao AUTO (antes o ESP32 ficava preso em OFF)
    assert client.post("/api/v1/comando-carga", json={"comando": "auto"}).json()["modo"] == "AUTO"


def test_comando_carga_invalido_e_offline():
    assert client.post("/api/v1/comando-carga", content="comando=XYZ", headers=FORM).status_code == 400
    assert client.post("/api/v1/comando-carga", content="comando=ON", headers=FORM).status_code == 503


def test_mensagem_oled():
    esp_envia()
    r = client.post("/api/v1/mensagem", content="mensagem=Ol%C3%A1%20turma", headers=FORM)
    assert r.status_code == 200 and r.json()["exibindo"] == "Olá turma"
    assert device.desired()["mensagem_web"] == "Olá turma"
    avisos = client.get("/api/v1/database/avisos-oled", params={"sala_id": 101}).json()
    assert avisos[0]["mensagem"] == "Olá turma"
    assert client.post("/api/v1/mensagem", content="mensagem=" + "x" * 65, headers=FORM).status_code == 400
    assert client.post("/api/v1/mensagem", content="mensagem=%20%20", headers=FORM).status_code == 400


def test_ac_on_e_cut_na_sala_do_esp32():
    esp_envia()
    assert client.post("/api/v1/rooms/101/ac/cut", content="room_id=101", headers=FORM).status_code == 200
    assert device.desired()["ac"] == "OFF"
    # repetir o corte na sala do ESP32 não dá 409 (estado real vem da telemetria)
    assert client.post("/api/v1/rooms/101/ac/cut").status_code == 200
    r = client.post("/api/v1/rooms/101/ac/on", content="room_id=101", headers=FORM)
    assert r.status_code == 200 and r.json()["ac"] == "ligado"
    assert device.desired()["ac"] == "ON"


def test_ac_da_sala_do_esp32_offline_da_503():
    assert client.post("/api/v1/rooms/101/ac/cut").status_code == 503
    assert client.post("/api/v1/rooms/101/ac/on").status_code == 503


def test_comando_retido_no_broker_e_recuperado():
    handle_mqtt_message(TOPICO_COMANDOS, b'{"modo_carga":"OFF","ac":"OFF","mensagem_web":"oi"}')
    assert device.desired() == {"modo_carga": "OFF", "ac": "OFF", "mensagem_web": "oi"}


def test_energia_acumulada_cresce():
    esp_envia(potencia_w=3600.0)
    device._state["last_seen"] -= 10   # 10 s depois...
    esp_envia(potencia_w=3600.0)
    assert client.get("/api/v1/telemetria").json()["energia_kwh"] > 0.009


def test_front_end_servido_pelo_backend():
    r = client.get("/")
    assert r.status_code == 200 and "CampusSmart" in r.text
    assert client.get("/js/config.js").status_code == 200


def test_pagina_do_banco():
    esp_envia(potencia_w=1100.0)
    r = client.get("/banco")
    assert r.status_code == 200
    assert "Tabela telemetrias" in r.text and "Sala 101" in r.text and "1100.0" in r.text
