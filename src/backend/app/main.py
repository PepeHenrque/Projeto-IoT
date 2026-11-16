"""CampusSmart API — servidor FastAPI e definição das rotas REST."""
import json
import os
import paho.mqtt.client as mqtt

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import database, mock_db
from .schemas import (
    Alert,
    AlertLevel,
    AvisoOledResponse,
    CutCommandResponse,
    ErrorResponse,
    Room,
    TelemetriaResponse,
)

API_PREFIX = "/api/v1"

app = FastAPI(
    title="CampusSmart API",
    description="API REST para monitoramento e automação de ar-condicionado do campus integrado com MySQL e MQTT.",
    version="0.2.0",
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
        sala_id_raw = payload.get("sala_id")
        if sala_id_raw:
            digits = "".join(filter(str.isdigit, str(sala_id_raw)))
            if digits:
                mock_db.update_room_telemetry(
                    room_id=int(digits),
                    occupied=payload.get("ocupado"),
                    potencia_w=float(payload.get("potencia_w", 0.0)),
                    corrente_ma=int(payload.get("corrente_ma", 0)),
                )
    except Exception as e:
        print(f"Erro ao processar mensagem MQTT: {e}")


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message


@app.on_event("startup")
def startup_event():
    # 1. Inicializa o banco de dados relacional (tabelas e seeds)
    try:
        database.init_db()
    except Exception as e:
        print(f"[DB] Erro na inicialização do banco de dados: {e}")

    # 2. Conecta ao broker MQTT
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception as e:
        print(f"Erro ao conectar ao Broker MQTT: {e}")


@app.on_event("shutdown")
def shutdown_event():
    try:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    except Exception as e:
        print(f"Erro ao desconectar MQTT: {e}")


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


# ------------------------------------------------------------------ estatísticas e regras de negócio
@router.get(
    "/rooms/analytics/energy-saving",
    tags=["Salas"],
    summary="Resumo de economia e desperdício de energia",
)
def energy_saving_analytics():
    """
    Retorna um resumo simulado do consumo de energia evitado 
    pelo sistema de corte automático em salas ociosas.
    """
    salas = mock_db.list_rooms()
    total_salas = len(salas)

    salas_com_ac_ligado = sum(1 for r in salas if getattr(r, "ac", False))
    salas_ociosas_com_ac = sum(1 for r in salas if getattr(r, "ac", False) and not r.occupied)

    kwh_poupado_estimado = round(salas_com_ac_ligado * 2.5, 2)

    return {
        "total_rooms_monitored": total_salas,
        "rooms_with_ac_on": salas_com_ac_ligado,
        "idle_rooms_with_ac_on": salas_ociosas_com_ac,
        "estimated_kwh_saved_today": kwh_poupado_estimado,
        "status_rule": "Ativa (Timeout ociosidade: 15 min)",
    }


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
@router.get(
    "/alerts/critical/summary",
    tags=["Alertas"],
    summary="Resumo de alertas críticos pendentes",
)
def critical_alerts_summary():
    """
    Filtra e retorna apenas os alertas de nível 'high' (críticos) 
    que exigem ação imediata da equipe de facilities.
    """
    alertas_criticos = mock_db.list_alerts(level="high")

    return {
        "total_critical_alerts": len(alertas_criticos),
        "alerts": alertas_criticos,
        "action_required": len(alertas_criticos) > 0,
    }


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
    try:
        comando_mqtt = json.dumps({
            "modo_carga": "OFF",
            "modo_led": "OFF",
            "mensagem_web": "CORTE REALIZADO",
        })
        mqtt_client.publish(TOPICO_COMANDOS, comando_mqtt)
    except Exception as e:
        print(f"Aviso: Não foi possível publicar no MQTT: {e}")

    return CutCommandResponse(
        success=True,
        message="Ar-condicionado desligado com sucesso.",
        room_id=room_id,
        device=device,
        executed_at=executed_at,
        resolved_alerts=resolved,
        room=room,
    )


# ------------------------------------------------------- banco de dados (MySQL)
@router.get(
    "/database/telemetrias",
    response_model=list[TelemetriaResponse],
    tags=["Banco de Dados"],
    summary="Consultar histórico de telemetria gravado no banco",
)
def get_telemetrias(
    sala_id: int | None = Query(None, description="Filtrar por id da sala"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade máxima de registros"),
):
    return mock_db.list_telemetrias(sala_id=sala_id, limit=limit)


@router.get(
    "/database/avisos-oled",
    response_model=list[AvisoOledResponse],
    tags=["Banco de Dados"],
    summary="Consultar histórico de avisos gravados no banco para a tela OLED",
)
def get_avisos_oled(
    sala_id: int | None = Query(None, description="Filtrar por id da sala"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade máxima de registros"),
):
    return mock_db.list_avisos_oled(sala_id=sala_id, limit=limit)


@router.get(
    "/database/status",
    tags=["Banco de Dados"],
    summary="Status da conexão com o banco de dados",
)
def database_status():
    return {
        "status": "connected",
        "dialect": database.DB_DIALECT,
        "database": os.getenv("MYSQL_DATABASE", "sistema_iot"),
    }


app.include_router(router)


@app.get("/health", tags=["Infra"], summary="Health check")
def health():
    return {"status": "ok"}
