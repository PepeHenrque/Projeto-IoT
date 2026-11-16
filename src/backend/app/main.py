"""CampusSmart API — servidor FastAPI e definição das rotas REST."""
import json
import os
import paho.mqtt.client as mqtt

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import mock_db
from .schemas import Alert, AlertLevel, CutCommandResponse, ErrorResponse, Room

API_PREFIX = "/api/v1"

app = FastAPI(
    title="CampusSmart API",
    description="API REST para monitoramento e automação de ar-condicionado do campus.",
    version="0.1.0",
)

# ----------------------------------------------------------------- MQTT Client
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
TOPICO_TELEMETRIA = "campussmart/sala101/telemetria"
TOPICO_COMANDOS = "campussmart/sala101/comandos"

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        client.subscribe(TOPICO_TELEMETRIA)

def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())
        # Atualiza a telemetria recebida do ESP32 via MQTT no mock_db (se necessário)
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

@app.on_event("startup")
def startup_event():
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Erro ao conectar ao Broker MQTT: {e}")

@app.on_event("shutdown")
def shutdown_event():
    mqtt_client.loop_stop()
    mqtt_client.disconnect()


_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix=API_PREFIX)


# ------------------------------------------------------------------ salas
@router.get("/rooms", response_model=list[Room], tags=["Salas"], summary="Listar salas")
def list_rooms(
    occupied: bool | None = Query(None, description="Filtrar por ocupação"),
    has_alerts: bool | None = Query(None, description="Somente salas com (ou sem) alertas"),
    q: str | None = Query(None, description="Busca por nome ou número da sala"),
):
    return mock_db.list_rooms(occupied=occupied, has_alerts=has_alerts, q=q)


@router.get(
    "/rooms/{room_id}",
    response_model=Room,
    responses={404: {"model": ErrorResponse}},
    tags=["Salas"],
    summary="Detalhar uma sala",
)
def get_room(room_id: int):
    try:
        return mock_db.get_room(room_id)
    except mock_db.RoomNotFound:
        raise HTTPException(404, f"Sala {room_id} não encontrada.")


# ----------------------------------------------------------------- alertas
@router.get("/alerts", response_model=list[Alert], tags=["Alertas"], summary="Buscar alertas")
def list_alerts(
    level: AlertLevel | None = Query(None, description="high | medium | low"),
    room_id: int | None = Query(None, description="Filtrar por sala"),
):
    return mock_db.list_alerts(level=level.value if level else None, room_id=room_id)


# ---------------------------------------------------------------- comandos
@router.post(
    "/rooms/{room_id}/ac/cut",
    response_model=CutCommandResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Sala não encontrada"},
        409: {"model": ErrorResponse, "description": "Ar-condicionado já está desligado"},
        422: {"model": ErrorResponse, "description": "Sala sem ar-condicionado"},
        503: {"model": ErrorResponse, "description": "Dispositivo não respondeu"},
    },
    tags=["Comandos"],
    summary="Disparar comando de corte (desligar ar-condicionado)",
)
def cut_ac(
    room_id: int,
    simulate_error: bool = Query(False, description="Simula falha de comunicação (para testar o modal de erro)"),
):
    if simulate_error:
        raise HTTPException(503, "Dispositivo não respondeu ao comando.")
    try:
        room, device, resolved, executed_at = mock_db.cut_ac(room_id)
    except mock_db.RoomNotFound:
        raise HTTPException(404, f"Sala {room_id} não encontrada.")
    except mock_db.NoAcInRoom:
        raise HTTPException(422, f"A sala {room_id} não possui ar-condicionado.")
    except mock_db.AcAlreadyOff:
        raise HTTPException(409, f"O ar-condicionado da sala {room_id} já está desligado.")

    # Dispara a ordem de desligamento via MQTT diretamente pro ESP32
    comando_mqtt = json.dumps({"modo_led": "OFF", "mensagem_web": "CORTE REALIZADO"})
    mqtt_client.publish(TOPICO_COMANDOS, comando_mqtt)

    return CutCommandResponse(
        success=True,
        message="Ar-condicionado desligado com sucesso.",
        room_id=room_id,
        device=device,
        executed_at=executed_at,
        resolved_alerts=resolved,
        room=room,
    )


app.include_router(router)


@app.get("/health", tags=["Infra"], summary="Health check")
def health():
    return {"status": "ok"}
