# CampusSmart — Hardware (ESP32)

Firmware `main.ino` para ESP32 com sensor PIR, display OLED 128x64 (I2C) e ventoinha/LED (ar-condicionado simulado).

## Ligações
| Componente | Pino do ESP32 |
|---|---|
| Sensor PIR (OUT) | GPIO 4 |
| LED (hoje) ou relé canal 1 — ventoinha 1 (IN1) | GPIO 18 |
| Relé canal 2 — ventoinha 2 (IN2) | GPIO 19 (`pinoRele2 = -1` se não usar) |
| LED "luz da sala" (presença) → resistor 220 Ω → GND | GPIO 23 (acende sozinho com o PIR; o app não controla) |
| Relé VCC / GND | VIN (5 V) / GND |
| OLED SDA / SCL | GPIO 21 / GPIO 22 (endereço 0x3C) |

### Quando o módulo relé chegar
1. **Mude o fio do LED do GPIO 18 para o GPIO 23** (ele vira a "luz da sala", que acende com presença).
   Ligue IN1 no GPIO 18 e IN2 no GPIO 19; VCC no **VIN (5 V)** e GND no GND do ESP32.
2. Cada ventoinha: o **+ da fonte** da ventoinha vai no **COM** do relé e o **NO** vai no + da ventoinha; o − vai direto na fonte. A ventoinha usa a própria fonte, não a alimentação do ESP32 (no máximo o VIN, se for uma ventoinha pequena de 5 V).
3. No `main.ino`, mude `RELE_ATIVO_EM_LOW` para `true` (a maioria dos módulos azuis de 5 V liga com LOW). Se a ventoinha ficar invertida (gira quando devia parar), volte para `false`.
4. Grave e teste pelo app: ON → as ventoinhas giram; OFF → param; AUTO → giram com movimento e param 30 s depois.
   "Desligar ar-condicionado" para **só as ventoinhas**: o PIR e o LED de presença continuam funcionando.

> Alguns módulos de 5 V não reconhecem os 3,3 V do ESP32. Se o LED do relé acender mas ele não "clicar", use um módulo com optoacoplador/jumper JD-VCC ou um módulo de 3,3 V.

## Bibliotecas (Arduino IDE → Gerenciador de Bibliotecas)
- **PubSubClient** (Nick O'Leary)
- **ArduinoJson** (Benoit Blanchon), versão 6 ou 7
- **Adafruit SSD1306** e **Adafruit GFX**
- Placa: **esp32 by Espressif Systems** (Gerenciador de Placas)

## Configurar antes de gravar
1. `WIFI_SSID` e `WIFI_PASS`: rede **2,4 GHz**.
2. Rede da instituição:
   - **Login em página do navegador** (captive portal): o ESP32 não passa por ela. Use o roteador do celular (2,4 GHz) ou peça à TI para liberar o **MAC** do ESP32, que aparece no Serial Monitor ao ligar.
   - **Usuário e senha na própria conexão Wi-Fi** (WPA2-Enterprise / PEAP): descomente `#define USAR_WPA2_ENTERPRISE` e preencha `EAP_USUARIO` e `EAP_SENHA`.
3. `TOPICO_BASE` precisa ser igual ao do back-end (`campussmart/cs7f3a/sala101`).

## Funcionamento
- **Modo AUTO:** a ventoinha liga com movimento no PIR e desliga **30 s** após o último movimento (`TEMPO_OCIOSIDADE_MS`).
- **ON / OFF:** força a carga ligada/cortada (comando do app).
- **Ar-condicionado ligado/desligado** pelo app: a ventoinha só gira se o AC estiver habilitado **e** a carga energizada.
- Telemetria a cada 2 s em `.../telemetria`; comandos em `.../comandos` (com retain: ao reconectar, o ESP32 recebe o último comando); `online`/`offline` em `.../status` (Last Will).
- Sem Wi-Fi ou sem broker o ESP32 **não trava**: o modo AUTO continua funcionando localmente e ele tenta reconectar sozinho.
- No OLED: `W` = Wi-Fi conectado, `M` = MQTT conectado; mensagens do app rolam na última linha (acentos são removidos, a fonte do display não tem acentos).

## Serial Monitor (115200)
- `[MQTT] ... falhou (estado -2)`: o ESP32 não alcançou o broker. Normalmente é a rede bloqueando a porta 1883 → use o roteador do celular.

## Sem a placa: simulador
`simulador_esp32.py` faz a mesma coisa que o firmware (mesmos tópicos). Com o venv do back-end ativo:
```bash
python src/hardware/simulador_esp32.py
```
Digite `p` + Enter para simular movimento, `o` para presença contínua, `q` para sair.
