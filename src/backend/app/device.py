"""Estado do dispositivo físico (ESP32 da Sala 101) recebido via MQTT.

O ESP32 publica a telemetria a cada 2 s. Este módulo guarda a última leitura, integra o consumo
acumulado (kWh) e mantém o "estado desejado" (modo da carga, ar-condicionado e mensagem do OLED),
que o back-end publica no tópico de comandos com retain=True. Assim, se o ESP32 reiniciar ou
reconectar, o broker entrega o último comando automaticamente.
"""
import os
import threading
import time
from datetime import datetime, timezone

DEVICE_ROOM_ID = 101                       # sala onde está o ESP32
OFFLINE_AFTER_S = float(os.getenv("DEVICE_OFFLINE_AFTER_S", "15"))   # sem telemetria há X s = offline
MODOS = ("AUTO", "ON", "OFF")
OLED_MAX = 64

_lock = threading.Lock()


def _defaults() -> dict:
    return {
        "last_seen": None,       # time.monotonic() da última telemetria
        "status": None,          # "online"/"offline" vindo do tópico de status (LWT)
        "ocupada": None,
        "ac_ligado": None,
        "carga_ligada": None,
        "modo": None,
        "potencia_w": None,
        "corrente_ma": None,
        "energia_kwh": 0.0,
        "ts": None,
        "desired": {"modo_carga": "AUTO", "ac": "ON", "mensagem_web": ""},
    }


_state = _defaults()


def reset() -> None:
    with _lock:
        _state.clear()
        _state.update(_defaults())


def _bool(v):
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str) and v.strip().lower() in ("true", "1", "on", "ligado", "sim"):
        return True
    if isinstance(v, str) and v.strip().lower() in ("false", "0", "off", "desligado", "nao", "não"):
        return False
    return None


def carga_ligada(modo: str, ocupada) -> bool:
    """Regra da carga: ON = energizada | OFF = cortada | AUTO = energizada só com a sala ocupada."""
    return modo == "ON" or (modo == "AUTO" and ocupada is True)


def apply_telemetry(payload: dict) -> None:
    """Atualiza o estado com uma mensagem de telemetria do ESP32."""
    now = time.monotonic()
    with _lock:
        s = _state
        potencia = payload.get("potencia_w")
        try:
            potencia = float(potencia) if potencia is not None else None
        except (TypeError, ValueError):
            potencia = None
        # Consumo acumulado = potência x tempo. Intervalo limitado a 60 s para não "saltar" depois de um período offline.
        if s["last_seen"] is not None and s["potencia_w"] is not None:
            dt_h = min(max(now - s["last_seen"], 0.0), 60.0) / 3600.0
            s["energia_kwh"] = round(s["energia_kwh"] + s["potencia_w"] / 1000.0 * dt_h, 5)
        s["last_seen"] = now
        s["ts"] = datetime.now(timezone.utc)
        s["status"] = "online"
        s["potencia_w"] = potencia
        try:
            s["corrente_ma"] = int(payload["corrente_ma"]) if payload.get("corrente_ma") is not None else None
        except (TypeError, ValueError):
            s["corrente_ma"] = None
        s["ocupada"] = _bool(payload.get("ocupado", payload.get("ocupada")))
        modo = str(payload.get("modo") or payload.get("modo_carga") or "").upper()
        s["modo"] = modo if modo in MODOS else None
        s["ac_ligado"] = _bool(payload.get("ac_ligado"))
        s["carga_ligada"] = _bool(payload.get("carga_ligada"))


def apply_status(text: str) -> None:
    with _lock:
        _state["status"] = text.strip().lower() or None


def apply_retained_command(payload: dict) -> None:
    """Recupera o último comando guardado no broker (retain) quando o back-end reinicia."""
    with _lock:
        d = _state["desired"]
        modo = str(payload.get("modo_carga") or "").upper()
        if modo in MODOS:
            d["modo_carga"] = modo
        ac = str(payload.get("ac") or "").upper()
        if ac in ("ON", "OFF"):
            d["ac"] = ac
        if isinstance(payload.get("mensagem_web"), str):
            d["mensagem_web"] = payload["mensagem_web"][:OLED_MAX]


def is_online() -> bool:
    with _lock:
        if _state["status"] == "offline":
            return False
        last = _state["last_seen"]
        return last is not None and (time.monotonic() - last) < OFFLINE_AFTER_S


def set_desired(**changes) -> dict:
    with _lock:
        _state["desired"].update(changes)
        return dict(_state["desired"])


def desired() -> dict:
    with _lock:
        return dict(_state["desired"])


def snapshot() -> dict:
    """Telemetria no formato esperado pelo front-end (js/services/campusApi.js → normalizeTelemetry)."""
    with _lock:
        s = _state
        d = s["desired"]
        modo = s["modo"] or d["modo_carga"]
        ac = s["ac_ligado"] if s["ac_ligado"] is not None else d["ac"] == "ON"
        ligada = s["carga_ligada"] if s["carga_ligada"] is not None else carga_ligada(modo, s["ocupada"])
        out = {
            "sala": DEVICE_ROOM_ID,
            "timestamp": (s["ts"] or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z"),
            "ocupada": s["ocupada"],
            "potencia_w": s["potencia_w"],
            "energia_kwh": round(s["energia_kwh"], 4),
            "corrente_ma": s["corrente_ma"],
            "ac": {"ligado": ac},
            "carga": {"modo": modo, "ligada": ligada},
            "mensagem_oled": d["mensagem_web"],
            "fonte": "esp32",
        }
        return out
