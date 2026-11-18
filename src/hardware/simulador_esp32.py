"""Simulador do ESP32 da Sala 101 (mesma lógica e mesmos tópicos MQTT do main.ino).

Serve para testar back-end + front-end sem a placa, ou como plano B na apresentação.

Uso (com o venv do back-end ativo, que já tem o paho-mqtt):
    python src/hardware/simulador_esp32.py

Teclas (digite e aperte Enter):
    p  = simula movimento no sensor PIR
    o  = alterna "pessoa parada na sala" (presença contínua)
    q  = sair
"""
import json
import os
import sys
import threading
import time

import paho.mqtt.client as mqtt

BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
PORT = int(os.getenv("MQTT_PORT", "1883"))
BASE = os.getenv("MQTT_TOPIC_BASE", "campussmart/cs7f3a/sala101")
TEMPO_OCIOSIDADE_S = float(os.getenv("TEMPO_OCIOSIDADE_S", "30"))
POTENCIA_AC_W = 1100.0

estado = {"modo": "AUTO", "ac": True, "msg": "", "ultimo_mov": None, "presenca_fixa": False}


def presenca() -> bool:
    if estado["presenca_fixa"]:
        return True
    t = estado["ultimo_mov"]
    return t is not None and time.monotonic() - t < TEMPO_OCIOSIDADE_S


def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] conectado a {BROKER} (rc={rc}); tópicos {BASE}/#")
    client.publish(f"{BASE}/status", "online", retain=True)
    client.subscribe(f"{BASE}/comandos")


def on_message(client, userdata, msg):
    try:
        d = json.loads(msg.payload.decode())
    except Exception:
        return
    modo = str(d.get("modo_carga") or d.get("modo_led") or "").upper()
    if modo in ("AUTO", "ON", "OFF"):
        estado["modo"] = modo
    ac = str(d.get("ac") or "").upper()
    if ac in ("ON", "OFF"):
        estado["ac"] = ac == "ON"
    if isinstance(d.get("mensagem_web"), str):
        estado["msg"] = d["mensagem_web"][:64]
    print(f"[CMD] modo={estado['modo']} ac={'ON' if estado['ac'] else 'OFF'} oled=\"{estado['msg']}\"")


def teclado():
    for linha in sys.stdin:
        c = linha.strip().lower()
        if c == "p":
            estado["ultimo_mov"] = time.monotonic()
            print("[PIR] movimento detectado")
        elif c == "o":
            estado["presenca_fixa"] = not estado["presenca_fixa"]
            print(f"[PIR] presença contínua = {estado['presenca_fixa']}")
        elif c == "q":
            os._exit(0)


def main():
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-esp32-{os.getpid()}")
    client.will_set(f"{BASE}/status", "offline", retain=True)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 30)
    client.loop_start()
    threading.Thread(target=teclado, daemon=True).start()
    print(__doc__.split("Teclas")[1])
    while True:
        ocupada = presenca()
        energizada = estado["modo"] == "ON" or (estado["modo"] == "AUTO" and ocupada)
        rodando = estado["ac"] and energizada
        pot = POTENCIA_AC_W if rodando else 0.0
        client.publish(f"{BASE}/telemetria", json.dumps({
            "sala_id": "SALA_101", "ocupado": ocupada, "modo": estado["modo"], "ac_ligado": estado["ac"],
            "carga_ligada": energizada, "potencia_w": pot, "corrente_ma": int(pot / 220 * 1000),
        }))
        time.sleep(2)


if __name__ == "__main__":
    main()
