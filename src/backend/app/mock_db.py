"""Camada de repositório e serviços de dados do CampusSmart.

Integra a modelagem relacional do banco de dados (tabelas: salas, telemetrias, avisos_oled)
com cache em memória e regras de negócio para as rotas da API (main.py).
"""
import copy
import threading
from datetime import datetime, timezone

from . import database
from .database import AvisoOledDB, SalaDB, SessionLocal, TelemetriaDB
from .schemas import Alert, Device, Room


# ---------- erros de domínio (traduzidos para HTTP em main.py) ----------
class RoomNotFound(Exception):
    pass


class NoAcInRoom(Exception):
    pass


class AcAlreadyOff(Exception):
    pass


# ---------- dados iniciais em memória ----------
def _d(name: str, status: str, on: bool) -> dict:
    return {"name": name, "status": status, "on": on}


# Única sala monitorada: a Sala 101, onde está o ESP32. O único equipamento controlado é o
# ar-condicionado (ventoinha). Ocupação e estado do AC são atualizados pela telemetria MQTT.
_SEED_ROOMS = [
    {"id": 101, "name": "Sala 101", "floor": "1º andar", "occupied": False, "lights": False, "last": "aguardando ESP32",
     "devices": [_d("Ar-condicionado", "Desligado", False)]},
]

# Alertas reais são calculados pelo front-end a partir da telemetria (sala vazia + AC ligado).
_SEED_ALERTS: list[dict] = []

_lock = threading.Lock()
_rooms: dict[int, dict] = {}
_alerts: list[dict] = []


def reset() -> None:
    with _lock:
        _rooms.clear()
        _rooms.update({r["id"]: copy.deepcopy(r) for r in _SEED_ROOMS})
        _alerts.clear()
        _alerts.extend(copy.deepcopy(_SEED_ALERTS))


reset()


# ---------- helpers ----------
def _find_ac(room: dict) -> dict | None:
    for dev in room["devices"]:
        n = dev["name"].lower()
        if "ar-condicionado" in n or "climatiza" in n:
            return dev
    return None


def _to_room(room: dict) -> Room:
    ac = _find_ac(room)
    return Room(
        id=room["id"],
        name=room["name"],
        floor=room["floor"],
        occupied=room["occupied"],
        alerts=sum(1 for a in _alerts if a["room_id"] == room["id"]),
        lights=room["lights"],
        ac=bool(ac and ac["on"]),
        last=room["last"],
        devices=[Device(**d) for d in room["devices"]],
    )


# ---------- consultas de salas e alertas ----------
def list_rooms(occupied: bool | None = None, has_alerts: bool | None = None, q: str | None = None) -> list[Room]:
    with _lock:
        result = [_to_room(r) for r in _rooms.values()]
    if occupied is not None:
        result = [r for r in result if r.occupied == occupied]
    if has_alerts is not None:
        result = [r for r in result if (r.alerts > 0) == has_alerts]
    if q:
        q = q.lower()
        result = [r for r in result if q in r.name.lower() or q in str(r.id)]
    return sorted(result, key=lambda r: r.id)


def get_room(room_id: int) -> Room:
    with _lock:
        room = _rooms.get(room_id)
        if room is None:
            raise RoomNotFound(room_id)
        return _to_room(room)


def list_alerts(level: str | None = None, room_id: int | None = None) -> list[Alert]:
    with _lock:
        items = [
            Alert(**a, room_name=_rooms[a["room_id"]]["name"])
            for a in _alerts
            if (level is None or a["level"] == level) and (room_id is None or a["room_id"] == room_id)
        ]
    return items


# ---------- integração com banco de dados: telemetria e avisos ----------
def update_room_telemetry(
    room_id: int,
    occupied: bool | None = None,
    potencia_w: float = 0.0,
    corrente_ma: int = 0,
    ac_on: bool | None = None,
) -> None:
    with _lock:
        room = _rooms.get(room_id)
        if room and occupied is not None:
            room["occupied"] = bool(occupied)
            room["last"] = "em uso" if occupied else "há pouco"
        if room and ac_on is not None:
            ac = _find_ac(room)
            if ac is not None:
                ac["on"] = bool(ac_on)
                ac["status"] = "Ligado" if ac_on else "Desligado"

    # Persistência nas tabelas relacionais salas e telemetrias
    session = SessionLocal()
    try:
        sala_db = session.query(SalaDB).filter(SalaDB.id == room_id).first()
        if sala_db:
            if occupied is not None:
                sala_db.status_ocupado = bool(occupied)
        else:
            sala_db = SalaDB(
                id=room_id,
                nome=f"Sala {room_id}",
                modo_operacao="AUTO",
                status_ocupado=bool(occupied) if occupied is not None else False,
            )
            session.add(sala_db)

        nova_telemetria = TelemetriaDB(
            sala_id=room_id,
            ocupado=bool(occupied) if occupied is not None else False,
            potencia_w=float(potencia_w),
            corrente_ma=int(corrente_ma),
            timestamp=datetime.utcnow(),
        )
        session.add(nova_telemetria)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[DB] Erro ao persistir telemetria: {e}")
    finally:
        session.close()


def record_aviso_oled(room_id: int, mensagem: str, modo_operacao: str | None = None) -> None:
    """Grava a mensagem enviada ao display OLED e, se informado, o novo modo de operação da sala."""
    session = SessionLocal()
    try:
        sala_db = session.query(SalaDB).filter(SalaDB.id == room_id).first()
        if sala_db and modo_operacao in ("AUTO", "ON", "OFF"):
            sala_db.modo_operacao = modo_operacao
        aviso = AvisoOledDB(
            sala_id=room_id,
            mensagem=mensagem,
            timestamp=datetime.utcnow(),
        )
        session.add(aviso)
        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[DB] Erro ao persistir aviso OLED: {e}")
    finally:
        session.close()


def list_telemetrias(sala_id: int | None = None, limit: int = 50) -> list[dict]:
    session = SessionLocal()
    try:
        q = session.query(TelemetriaDB)
        if sala_id is not None:
            q = q.filter(TelemetriaDB.sala_id == sala_id)
        items = q.order_by(TelemetriaDB.id.desc()).limit(limit).all()
        return [
            {
                "id": t.id,
                "sala_id": t.sala_id,
                "ocupado": t.ocupado,
                "potencia_w": t.potencia_w,
                "corrente_ma": t.corrente_ma,
                "timestamp": t.timestamp,
            }
            for t in items
        ]
    except Exception as e:
        print(f"[DB] Erro ao consultar telemetrias: {e}")
        return []
    finally:
        session.close()


def list_avisos_oled(sala_id: int | None = None, limit: int = 50) -> list[dict]:
    session = SessionLocal()
    try:
        q = session.query(AvisoOledDB)
        if sala_id is not None:
            q = q.filter(AvisoOledDB.sala_id == sala_id)
        items = q.order_by(AvisoOledDB.id.desc()).limit(limit).all()
        return [
            {
                "id": a.id,
                "sala_id": a.sala_id,
                "mensagem": a.mensagem,
                "timestamp": a.timestamp,
            }
            for a in items
        ]
    except Exception as e:
        print(f"[DB] Erro ao consultar avisos OLED: {e}")
        return []
    finally:
        session.close()


# ---------- comandos do ar-condicionado ----------
def cut_ac(room_id: int, allow_already_off: bool = False) -> tuple[Room, str, int, datetime]:
    with _lock:
        room = _rooms.get(room_id)
        if room is None:
            raise RoomNotFound(room_id)
        ac = _find_ac(room)
        if ac is None:
            raise NoAcInRoom(room_id)
        if not ac["on"] and not allow_already_off:
            raise AcAlreadyOff(room_id)

        ac["on"] = False
        ac["status"] = "Desligado"

        before = len(_alerts)
        _alerts[:] = [a for a in _alerts if not (a["room_id"] == room_id and a["equip"] == ac["name"])]
        resolved = before - len(_alerts)

    # Grava o comando na tabela avisos_oled e atualiza a tabela salas no banco
    record_aviso_oled(room_id, f"CORTE: {ac['name']} desligado")

    return _to_room(room), ac["name"], resolved, datetime.now(timezone.utc)


def turn_on_ac(room_id: int) -> tuple[Room, str, datetime]:
    with _lock:
        room = _rooms.get(room_id)
        if room is None:
            raise RoomNotFound(room_id)
        ac = _find_ac(room)
        if ac is None:
            raise NoAcInRoom(room_id)
        ac["on"] = True
        ac["status"] = "Ligado"
    record_aviso_oled(room_id, f"LIGADO: {ac['name']}")
    return _to_room(room), ac["name"], datetime.now(timezone.utc)
