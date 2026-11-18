"""CampusSmart API — servidor FastAPI, integração MQTT com o ESP32 e definição das rotas REST."""
import json
import logging
import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qs

import paho.mqtt.client as mqtt
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import database, device, mock_db
from .schemas import (
    Alert,
    AlertLevel,
    AvisoOledResponse,
    CutCommandResponse,
    ErrorResponse,
    Room,
    TelemetriaResponse,
)

logger = logging.getLogger("campussmart.api")
API_PREFIX = "/api/v1"

# ----------------------------------------------------------------- MQTT
# Os tópicos precisam ser IGUAIS aos do firmware (src/hardware/main.ino → TOPICO_BASE).
# O broker público é compartilhado com o mundo todo: por isso o identificador "cs7f3a" no tópico.
MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPICO_BASE = os.getenv("MQTT_TOPIC_BASE", "campussmart/cs7f3a/sala101")
TOPICO_TELEMETRIA = f"{TOPICO_BASE}/telemetria"
TOPICO_COMANDOS = f"{TOPICO_BASE}/comandos"
TOPICO_STATUS = f"{TOPICO_BASE}/status"
MQTT_ENABLED = os.getenv("CAMPUS_DISABLE_MQTT", "0") != "1"


def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print(f"[MQTT] Conectado a {MQTT_BROKER}:{MQTT_PORT} — ouvindo {TOPICO_BASE}/#")
        client.subscribe([(TOPICO_TELEMETRIA, 0), (TOPICO_STATUS, 0), (TOPICO_COMANDOS, 0)])
    else:
        print(f"[MQTT] Falha ao conectar: {reason_code}")


def on_disconnect(client, userdata, flags, reason_code, properties=None):
    print(f"[MQTT] Desconectado ({reason_code}); o paho reconecta sozinho.")


def handle_mqtt_message(topic: str, raw: bytes) -> None:
    """Processa uma mensagem recebida (separado do callback para poder ser testado)."""
    text = raw.decode("utf-8", errors="replace")
    if topic == TOPICO_STATUS:
        device.apply_status(text)
        return
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        print(f"[MQTT] Mensagem ignorada (não é JSON) em {topic}: {text[:80]}")
        return
    if not isinstance(payload, dict):
        return
    if topic == TOPICO_COMANDOS:
        device.apply_retained_command(payload)   # recupera o último comando guardado no broker
        return
    if topic == TOPICO_TELEMETRIA:
        device.apply_telemetry(payload)
        snap = device.snapshot()
        mock_db.update_room_telemetry(
            room_id=device.DEVICE_ROOM_ID,
            occupied=snap["ocupada"],
            potencia_w=float(snap["potencia_w"] or 0.0),
            corrente_ma=int(snap["corrente_ma"] or 0),
            ac_on=bool(snap["ac"]["ligado"] and snap["carga"]["ligada"]),
        )


def on_message(client, userdata, msg):
    try:
        handle_mqtt_message(msg.topic, msg.payload)
    except Exception as e:  # nunca derrubar a thread do MQTT
        print(f"[MQTT] Erro ao processar mensagem: {e}")


mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.on_connect = on_connect
mqtt_client.on_disconnect = on_disconnect
mqtt_client.on_message = on_message
mqtt_client.reconnect_delay_set(min_delay=1, max_delay=10)


def publish_command() -> None:
    """Publica o estado desejado COMPLETO, com retain: o ESP32 recebe mesmo se reconectar depois."""
    payload = json.dumps(device.desired(), ensure_ascii=False)
    info = mqtt_client.publish(TOPICO_COMANDOS, payload, qos=1, retain=True)
    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        print(f"[MQTT] Aviso: comando não publicado (rc={info.rc}): {payload}")


PORTA_HTTP = os.getenv("PORT", "8000")


def ip_da_rede() -> str | None:
    """IP do computador na rede Wi-Fi (o que o celular usa). Não envia nada pela rede."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def link_celular() -> str | None:
    ip = ip_da_rede()
    return f"http://{ip}:{PORTA_HTTP}/" if ip else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    link = link_celular()
    print("=" * 64)
    print(f"  App no computador: http://localhost:{PORTA_HTTP}/")
    if link:
        print(f"  App no celular (mesmo Wi-Fi): {link}")
        print(f"  QR code para o celular: http://localhost:{PORTA_HTTP}/celular")
    print(f"  Dados gravados no banco: http://localhost:{PORTA_HTTP}/banco")
    print("=" * 64)
    try:
        database.init_db()
    except Exception as e:
        print(f"[DB] Erro na inicialização do banco de dados: {e}")
    if MQTT_ENABLED:
        # connect_async + loop_start: se o broker estiver fora, o paho continua tentando em segundo plano.
        mqtt_client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=30)
        mqtt_client.loop_start()
    yield
    if MQTT_ENABLED:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


app = FastAPI(
    title="CampusSmart API",
    description="API REST para monitoramento e automação de ar-condicionado do campus integrado com MySQL e MQTT.",
    version="0.3.0",
    lifespan=lifespan,
)


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(request: Request, exc: StarletteHTTPException):
    # "detail" (padrão FastAPI) + "erro" (lido pelo front-end para mostrar o motivo no modal)
    return JSONResponse({"detail": exc.detail, "erro": exc.detail}, status_code=exc.status_code, headers=exc.headers)


_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix=API_PREFIX)


async def read_body(request: Request) -> dict:
    """Aceita formulário (padrão do front, sem preflight CORS) ou JSON."""
    raw = await request.body()
    if not raw:
        return {}
    text = raw.decode("utf-8", errors="replace")
    if "application/json" in request.headers.get("content-type", "") or text.lstrip().startswith("{"):
        try:
            data = json.loads(text)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {k: v[0] for k, v in parse_qs(text, keep_blank_values=True).items()}


def require_device_online() -> None:
    if not device.is_online():
        raise HTTPException(503, "dispositivo offline (ESP32 sem enviar telemetria)")


# ------------------------------------------------------------------ dispositivo (Sala 101 / ESP32)
@router.get("/telemetria", tags=["Dispositivo"], summary="Última telemetria do ESP32 da Sala 101")
def get_telemetria():
    require_device_online()
    return device.snapshot()


@router.post("/comando-carga", tags=["Dispositivo"], summary="Modo da carga: ON | OFF | AUTO")
async def comando_carga(request: Request):
    body = await read_body(request)
    cmd = str(body.get("comando") or body.get("modo") or "").strip().upper()
    if cmd not in device.MODOS:
        raise HTTPException(400, "comando inválido (use ON, OFF ou AUTO)")
    require_device_online()
    device.set_desired(modo_carga=cmd)
    publish_command()
    mock_db.record_aviso_oled(device.DEVICE_ROOM_ID, f"MODO {cmd}", modo_operacao=cmd)
    ligada = device.carga_ligada(cmd, device.snapshot()["ocupada"])
    return {"ok": True, "modo": cmd, "carga": {"modo": cmd, "ligada": ligada}}


@router.post("/mensagem", tags=["Dispositivo"], summary="Envia uma mensagem ao display OLED")
async def mensagem_oled(request: Request):
    body = await read_body(request)
    texto = str(body.get("mensagem") or "").strip()
    if not texto or len(texto) > device.OLED_MAX:
        raise HTTPException(400, f"mensagem vazia ou maior que {device.OLED_MAX} caracteres")
    require_device_online()
    device.set_desired(mensagem_web=texto)
    publish_command()
    mock_db.record_aviso_oled(device.DEVICE_ROOM_ID, texto)
    return {"ok": True, "exibindo": texto}


# ------------------------------------------------------------------ salas
@router.get("/rooms", response_model=list[Room], tags=["Salas"], summary="Listar salas")
def list_rooms(
    occupied: bool | None = Query(None, description="Filtrar por ocupação"),
    has_alerts: bool | None = Query(None, description="Somente salas com (ou sem) alertas"),
    q: str | None = Query(None, description="Busca por nome ou número da sala"),
):
    return mock_db.list_rooms(occupied=occupied, has_alerts=has_alerts, q=q)


@router.get("/rooms/analytics/energy-saving", tags=["Salas"], summary="Resumo de economia e desperdício de energia")
def energy_saving_analytics():
    """Resumo simulado do consumo de energia evitado pelo corte automático em salas ociosas."""
    salas = mock_db.list_rooms()
    salas_com_ac_ligado = sum(1 for r in salas if r.ac)
    salas_ociosas_com_ac = sum(1 for r in salas if r.ac and not r.occupied)
    return {
        "total_rooms_monitored": len(salas),
        "rooms_with_ac_on": salas_com_ac_ligado,
        "idle_rooms_with_ac_on": salas_ociosas_com_ac,
        "estimated_kwh_saved_today": round(salas_com_ac_ligado * 2.5, 2),
        "status_rule": "Ativa (Timeout ociosidade: 15 min)",
    }


@router.get("/rooms/{room_id}", response_model=Room, responses={404: {"model": ErrorResponse}}, tags=["Salas"],
            summary="Detalhar uma sala")
def get_room(room_id: int):
    try:
        return mock_db.get_room(room_id)
    except mock_db.RoomNotFound:
        raise HTTPException(404, f"Sala {room_id} não encontrada.")


# ----------------------------------------------------------------- alertas
@router.get("/alerts/critical/summary", tags=["Alertas"], summary="Resumo de alertas críticos pendentes")
def critical_alerts_summary():
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


# ---------------------------------------------------------------- comandos do ar-condicionado
_AC_RESPONSES = {
    404: {"model": ErrorResponse, "description": "Sala não encontrada"},
    409: {"model": ErrorResponse, "description": "Ar-condicionado já está desligado"},
    422: {"model": ErrorResponse, "description": "Sala sem ar-condicionado"},
    503: {"model": ErrorResponse, "description": "Dispositivo não respondeu"},
}


@router.post("/rooms/{room_id}/ac/cut", response_model=CutCommandResponse, responses=_AC_RESPONSES, tags=["Comandos"],
             summary="Disparar comando de corte (desligar ar-condicionado)")
def cut_ac(
    room_id: int,
    simulate_error: bool = Query(False, description="Simula falha de comunicação (para testar o modal de erro)"),
):
    if simulate_error:
        raise HTTPException(503, "Dispositivo não respondeu ao comando.")
    is_device_room = room_id == device.DEVICE_ROOM_ID
    if is_device_room:
        require_device_online()
    try:
        # Na sala com o ESP32 o comando é idempotente: o estado real vem da telemetria.
        room, dev_name, resolved, executed_at = mock_db.cut_ac(room_id, allow_already_off=is_device_room)
    except mock_db.RoomNotFound:
        raise HTTPException(404, f"Sala {room_id} não encontrada.")
    except mock_db.NoAcInRoom:
        raise HTTPException(422, f"A sala {room_id} não possui ar-condicionado.")
    except mock_db.AcAlreadyOff:
        raise HTTPException(409, f"O ar-condicionado da sala {room_id} já está desligado.")

    if is_device_room:   # só a Sala 101 tem dispositivo físico; as outras salas são simuladas
        device.set_desired(ac="OFF", mensagem_web="CORTE REALIZADO")
        publish_command()

    return CutCommandResponse(success=True, message="Ar-condicionado desligado com sucesso.", room_id=room_id,
                              device=dev_name, executed_at=executed_at, resolved_alerts=resolved, room=room)


@router.post("/rooms/{room_id}/ac/on", responses=_AC_RESPONSES, tags=["Comandos"], summary="Ligar o ar-condicionado")
def ac_on(room_id: int):
    is_device_room = room_id == device.DEVICE_ROOM_ID
    if is_device_room:
        require_device_online()
    try:
        room, dev_name, executed_at = mock_db.turn_on_ac(room_id)
    except mock_db.RoomNotFound:
        raise HTTPException(404, f"Sala {room_id} não encontrada.")
    except mock_db.NoAcInRoom:
        raise HTTPException(422, f"A sala {room_id} não possui ar-condicionado.")
    if is_device_room:
        device.set_desired(ac="ON", mensagem_web="AC LIGADO")
        publish_command()
    return {"ok": True, "success": True, "room_id": room_id, "device": dev_name, "ac": "ligado",
            "executed_at": executed_at, "room": room}


# ------------------------------------------------------- banco de dados (MySQL)
@router.get("/database/telemetrias", response_model=list[TelemetriaResponse], tags=["Banco de Dados"],
            summary="Consultar histórico de telemetria gravado no banco")
def get_telemetrias(
    sala_id: int | None = Query(None, description="Filtrar por id da sala"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade máxima de registros"),
):
    return mock_db.list_telemetrias(sala_id=sala_id, limit=limit)


@router.get("/database/avisos-oled", response_model=list[AvisoOledResponse], tags=["Banco de Dados"],
            summary="Consultar histórico de avisos gravados no banco para a tela OLED")
def get_avisos_oled(
    sala_id: int | None = Query(None, description="Filtrar por id da sala"),
    limit: int = Query(50, ge=1, le=200, description="Quantidade máxima de registros"),
):
    return mock_db.list_avisos_oled(sala_id=sala_id, limit=limit)


@router.get("/database/status", tags=["Banco de Dados"], summary="Status da conexão com o banco de dados")
def database_status():
    try:
        with database.engine.connect():
            status = "connected"
    except Exception:
        status = "disconnected"
    return {"status": status, "dialect": database.DB_DIALECT, "database": os.getenv("MYSQL_DATABASE", "sistema_iot")}


@router.get("/device/status", tags=["Dispositivo"], summary="Diagnóstico: ESP32 online? MQTT conectado?")
def device_status():
    return {
        "esp32_online": device.is_online(),
        "mqtt_conectado": mqtt_client.is_connected(),
        "broker": f"{MQTT_BROKER}:{MQTT_PORT}",
        "topicos": {"telemetria": TOPICO_TELEMETRIA, "comandos": TOPICO_COMANDOS, "status": TOPICO_STATUS},
        "comando_atual": device.desired(),
    }


app.include_router(router)


@app.get("/health", tags=["Infra"], summary="Health check")
def health():
    return {"status": "ok"}


@app.get("/banco", response_class=HTMLResponse, include_in_schema=False)
def pagina_banco():
    """Mostra, de forma legível, o que está gravado no banco (tabelas salas, telemetrias e avisos_oled)."""
    from html import escape
    from sqlalchemy import func as sa_func
    session = database.SessionLocal()
    try:
        salas = session.query(database.SalaDB).order_by(database.SalaDB.id).all()
        total_tel = session.query(sa_func.count(database.TelemetriaDB.id)).scalar() or 0
        total_av = session.query(sa_func.count(database.AvisoOledDB.id)).scalar() or 0
        tels = session.query(database.TelemetriaDB).order_by(database.TelemetriaDB.id.desc()).limit(30).all()
        avisos = session.query(database.AvisoOledDB).order_by(database.AvisoOledDB.id.desc()).limit(30).all()
    finally:
        session.close()

    def tabela(cab, linhas):
        th = "".join(f"<th>{escape(c)}</th>" for c in cab)
        tr = "".join("<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in l) + "</tr>" for l in linhas)
        return f"<table><tr>{th}</tr>{tr or '<tr><td colspan=9>(vazio)</td></tr>'}</table>"

    from datetime import timezone as tz
    # O banco guarda em UTC; aqui mostramos no horário do computador.
    fmt = lambda t: (t.replace(tzinfo=tz.utc) if t.tzinfo is None else t).astimezone().strftime("%d/%m %H:%M:%S") if t else ""
    sim = lambda b: "sim" if b else "não"
    banco = "MySQL" if database.DB_DIALECT == "mysql" else "SQLite (arquivo src/backend/sistema_iot.db)"
    corpo = (
        f"<p>Banco em uso: <b>{banco}</b> · banco <code>{escape(os.getenv('MYSQL_DATABASE', 'sistema_iot'))}</code> · "
        f"<b>{total_tel}</b> telemetrias e <b>{total_av}</b> avisos gravados. A página atualiza a cada 5 s.</p>"
        "<h2>Tabela salas</h2>"
        + tabela(["id", "nome", "modo_operacao", "status_ocupado"],
                 [(x.id, x.nome, x.modo_operacao, sim(x.status_ocupado)) for x in salas])
        + "<h2>Tabela telemetrias (últimas 30, enviadas pelo ESP32 a cada 2 s)</h2>"
        + tabela(["id", "sala_id", "ocupado", "potencia_w", "corrente_ma", "horário"],
                 [(t.id, t.sala_id, sim(t.ocupado), t.potencia_w, t.corrente_ma, fmt(t.timestamp)) for t in tels])
        + "<h2>Tabela avisos_oled (últimos 30 comandos e mensagens do app)</h2>"
        + tabela(["id", "sala_id", "mensagem", "horário"],
                 [(a.id, a.sala_id, a.mensagem, fmt(a.timestamp)) for a in avisos])
    )
    return HTMLResponse(f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="refresh" content="5">
<title>CampusSmart · Banco de dados</title><style>
body{{font-family:system-ui,sans-serif;margin:24px;color:#0f172a}}h1{{margin:0 0 8px}}h2{{margin-top:28px;font-size:1.1rem}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{border:1px solid #cbd5e1;padding:6px 8px;text-align:left}}
th{{background:#eef2ff}}tr:nth-child(even) td{{background:#f8fafc}}code{{background:#eef2ff;padding:2px 6px;border-radius:4px}}
</style></head><body><h1>CampusSmart · Banco de dados</h1>{corpo}</body></html>""")


@app.get("/celular", response_class=HTMLResponse, include_in_schema=False)
def pagina_celular():
    """Mostra o link do app para o celular e um QR code (aponte a câmera do celular para a tela)."""
    link = link_celular()
    if not link:
        return HTMLResponse("<h1>Computador sem rede Wi-Fi</h1><p>Conecte o computador ao Wi-Fi e recarregue.</p>")
    try:
        import qrcode
        import qrcode.image.svg
        qr_svg = qrcode.make(link, image_factory=qrcode.image.svg.SvgPathImage, box_size=14).to_string(encoding="unicode")
    except ImportError:
        qr_svg = "<p>(instale o pacote <code>qrcode</code> para ver o QR code: pip install -r requirements.txt)</p>"
    return HTMLResponse(f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<title>CampusSmart no celular</title><meta http-equiv="refresh" content="30">
<style>body{{font-family:system-ui,sans-serif;text-align:center;padding:24px;color:#0f172a}}
.qr svg{{width:320px;height:320px}}code{{font-size:1.6rem;background:#eef2ff;padding:6px 12px;border-radius:8px}}</style>
</head><body><h1>CampusSmart · Sala 101</h1><p>Aponte a câmera do celular para o QR code<br>(o celular precisa estar no <b>mesmo Wi-Fi</b> deste computador)</p>
<div class="qr">{qr_svg}</div><p>ou digite no navegador do celular:</p><p><code>{link}</code></p></body></html>""")


# --------------------------------------------------------------- front-end
# Serve o front (src/frontend) em http://localhost:8000/ — no celular: http://IP-DO-COMPUTADOR:8000/
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", Path(__file__).resolve().parents[2] / "frontend"))
if (FRONTEND_DIR / "index.html").exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
