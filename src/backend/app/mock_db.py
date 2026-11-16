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


_SEED_ROOMS = [
    {"id": 101, "name": "Sala 101", "floor": "1º andar", "occupied": True, "lights": True, "last": "há 10min",
     "devices": [_d("Iluminação", "Ligada", True), _d("Ar-condicionado", "Ligado", True), _d("Projetor", "Desligado", False)]},
    {"id": 102, "name": "Sala 102", "floor": "1º andar", "occupied": False, "lights": True, "last": "há 45min",
     "devices": [_d("Iluminação", "Ligada", True), _d("Ar-condicionado", "Ligado", True), _d("Projetor", "Desligado", False)]},
    {"id": 103, "name": "Sala 103", "floor": "1º andar", "occupied": True, "lights": True, "last": "em uso",
     "devices": [_d("Iluminação", "Ligada", True), _d("Ar-condicionado", "Ligado", True)]},
    {"id": 104, "name": "Lab. Informática", "floor": "1º andar", "occupied": False, "lights": True, "last": "há 2h 15min",
     "devices": [_d("Iluminação", "Ligada", True), _d("Climatização", "Desligado", False), _d("Computadores (8)", "Ligados", True),
                 _d("Projetor", "Desligado", False), _d("Impressora", "Ligada", True), _d("Switch de rede", "Ligado", True)]},
    {"id": 105, "name": "Auditório", "floor": "Térreo", "occupied": False, "lights": False, "last": "há 1h 40min",
     "devices": [_d("Iluminação", "Desligada", False), _d("Ar-condicionado", "Ligado", True), _d("Palco", "Ligado", True)]},
    {"id": 201, "name": "Sala 201", "floor": "2º andar", "occupied": True, "lights": True, "last": "em uso",
     "devices": [_d("Iluminação", "Ligada", True), _d("Ar-condicionado", "Ligado", True)]},
    {"id": 202, "name": "Sala 202", "floor": "2º andar", "occupied": False, "lights": False, "last": "há 3h",
     "devices": [_d("Iluminação", "Desligada", False), _d("Ar-condicionado", "Desligado", False)]},
    {"id": 203, "name": "Biblioteca", "floor": "Térreo", "occupied": True, "lights": True, "last": "em uso",
     "devices": [_d("Iluminação", "Ligada", True), _d("Ar-condicionado", "Ligado", True), _d("Computadores", "Ligados", True)]},
]

_SEED_ALERTS = [
    {"id": 1, "room_id": 102, "equip": "Ar-condicionado", "title": "Sala ociosa com AC ligado", "priority": "Alta", "level": "high", "time": "há 45min"},
    {"id": 2, "room_id": 104, "equip": "Computadores (8)", "title": "Equipamentos ligados sem uso", "priority": "Alta", "level": "high", "time": "há 2h 15min"},
    {"id": 3, "room_id": 105, "equip": "Ar-condicionado", "title": "Sala ociosa com AC ligado", "priority": "Alta", "level": "high", "time": "há 1h 40min"},
    {"id": 4, "room_id": 104, "equip": "Iluminação", "title": "Sala ociosa com luz acesa", "priority": "Média", "level": "medium", "time": "há 2h 15min"},
    {"id": 5, "room_id": 105, "equip": "Iluminação", "title": "Iluminação sem evento ativo", "priority": "Média", "level": "medium", "time": "há 3h"},
    {"id": 6, "room_id": 203, "equip": "Computadores", "title": "Consumo acima do padrão", "priority": "Baixa", "level": "low", "time": "há 30min"},
    {"id": 7, "room_id": 101, "equip": "Iluminação", "title": "Consumo elevado", "priority": "Baixa", "level": "low", "time": "há 20min"},
]

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
) -> None:
    with _lock:
        room = _rooms.get(room_id)
        if room and occupied is not None:
            room["occupied"] = bool(occupied)
            room["last"] = "em uso" if occupied else "há pouco"

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


def record_aviso_oled(room_id: int, mensagem: str) -> None:
    session = SessionLocal()
    try:
        sala_db = session.query(SalaDB).filter(SalaDB.id == room_id).first()
        if sala_db:
            if "CORTE" in mensagem.upper() or "DESLIG" in mensagem.upper():
                sala_db.modo_operacao = "OFF"
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


# ---------- comando de corte ----------
def cut_ac(room_id: int) -> tuple[Room, str, int, datetime]:
    with _lock:
        room = _rooms.get(room_id)
        if room is None:
            raise RoomNotFound(room_id)
        ac = _find_ac(room)
        if ac is None:
            raise NoAcInRoom(room_id)
        if not ac["on"]:
            raise AcAlreadyOff(room_id)

        ac["on"] = False
        ac["status"] = "Desligado"

        before = len(_alerts)
        _alerts[:] = [a for a in _alerts if not (a["room_id"] == room_id and a["equip"] == ac["name"])]
        resolved = before - len(_alerts)

    # Grava o comando na tabela avisos_oled e atualiza a tabela salas no banco
    record_aviso_oled(room_id, f"CORTE: {ac['name']} desligado")

    return _to_room(room), ac["name"], resolved, datetime.now(timezone.utc)
