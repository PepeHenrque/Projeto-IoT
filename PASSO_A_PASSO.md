# CampusSmart — Passo a passo para testar tudo (ESP32 + back-end + app)

Siga na ordem. Cada etapa tem um "Deu certo se…" para você conferir antes de seguir.

---

## 0. O que você precisa
- ESP32 + sensor PIR + display OLED + LED/ventoinha (montagem atual).
- Cabo USB **de dados** (alguns cabos só carregam).
- Computador com **Python 3.10+** e **Arduino IDE 2**.
- Uma rede Wi-Fi **2,4 GHz sem página de login**: o mais garantido é o **roteador do celular**.
  - No iPhone: ative "Maximizar compatibilidade". No Android: banda 2,4 GHz.
  - O **computador também precisa estar com internet** (pode ser no mesmo roteador do celular).

---

## 1. Preparar a Arduino IDE (só na primeira vez)
1. **Placa ESP32:** `Ferramentas > Placa > Gerenciador de Placas` → procure **esp32** (Espressif Systems) → Instalar.
2. **Bibliotecas:** `Sketch > Incluir Biblioteca > Gerenciar Bibliotecas` e instale:
   - **PubSubClient** (Nick O'Leary)
   - **ArduinoJson** (Benoit Blanchon)
   - **Adafruit SSD1306** (aceite instalar as dependências, inclui a **Adafruit GFX**)
3. Selecione a placa **ESP32 Dev Module** (ou o modelo da sua) e a porta COM do ESP32.
   - A porta não aparece? Instale o driver **CP210x** ou **CH340** (depende do chip USB da placa).

---

## 2. Configurar e gravar o firmware
1. Abra `src/hardware/main.ino`.
2. Preencha o Wi-Fi (linhas do topo):
   ```cpp
   const char* WIFI_SSID = "NOME_DO_ROTEADOR_DO_CELULAR";
   const char* WIFI_PASS = "SENHA";
   ```
   - Rede com **usuário e senha na própria conexão** (WPA2-Enterprise, tipo eduroam)? Descomente `#define USAR_WPA2_ENTERPRISE` e preencha `EAP_USUARIO` / `EAP_SENHA`.
   - Rede com **página de login no navegador**: não funciona com o ESP32. Use o celular.
3. Por enquanto, com o **LED** no GPIO 18, deixe `RELE_ATIVO_EM_LOW = false`.
4. Clique em **Verificar** e depois em **Carregar** (→).
   - Fica em "Connecting....."? Segure o botão **BOOT** da placa até começar a gravar.
5. Abra o **Monitor Serial** em **115200**.

**Deu certo se** o Serial mostrar:
```
[Wi-Fi] MAC do ESP32 (para a TI liberar): XX:XX:XX:XX:XX:XX
[Wi-Fi] Conectado! IP: 192.168.x.x
[MQTT] Conectando ao broker... conectado!
```
e o OLED mostrar **W** e **M** no canto superior direito (Wi-Fi e MQTT conectados).

| Sintoma | Causa provável | O que fazer |
|---|---|---|
| Fica em `.....` e "Não conectou" | Rede 5 GHz, senha errada ou rede com login | Roteador do celular em 2,4 GHz |
| `falhou (estado -2)` | A rede bloqueia a porta 1883 do MQTT | Roteador do celular |
| OLED apagado / "Display OLED não encontrado" | Fios SDA/SCL | SDA → GPIO 21, SCL → GPIO 22, VCC 3,3 V |
| Erro de compilação | Biblioteca faltando ou versão diferente | Confira o passo 1; mande a mensagem de erro |

---

## 3. Testar o ESP32 sozinho (antes do app)
- Modo padrão é **AUTO**: passe a mão na frente do PIR → o LED acende e o OLED mostra `AC: ON` / `Ocupada`.
- Fique parado longe do sensor → **30 s** depois o LED apaga (`AC: OFF` / `Vazia`).
  - Para a apresentação, dá para reduzir em `TEMPO_OCIOSIDADE_MS` (ex.: `10000` = 10 s).
- Ajuste também os potenciômetros do PIR (sensibilidade e tempo) se ele disparar demais ou de menos.

---

## 4. Subir o back-end (que também serve o app)
No terminal (PowerShell), dentro da pasta do projeto:
```powershell
cd src\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
**Deu certo se** aparecer:
```
[DB] ... (MySQL ou "Utilizando SQLite local")
[MQTT] Conectado a broker.hivemq.com:1883 — ouvindo campussmart/cs7f3a/sala101/#
Uvicorn running on http://0.0.0.0:8000
```
- Sem MySQL instalado ele usa **SQLite** sozinho, e tudo funciona igual.
- Com MySQL: rode antes `src/database/BancoProjetoIot.sql` no Workbench. A senha padrão esperada é `root`; se for outra:
  `$env:MYSQL_PASSWORD="sua_senha"` antes do `uvicorn`.
- Windows pediu permissão de firewall? **Permitir** (para o celular acessar).

**Conferência rápida:** abra http://localhost:8000/api/v1/device/status
`"esp32_online": true` e `"mqtt_conectado": true`.

---

## 5. Abrir o app
- No computador: **http://localhost:8000/**
- No celular (mesmo Wi-Fi do computador): abra no PC **http://localhost:8000/celular** e aponte a câmera do celular para o **QR code**.
  O link também aparece no terminal quando o servidor liga ("App no celular: http://...").
- Celular não abre? Em Configurações → Rede e Internet → Wi-Fi → sua rede, deixe o perfil como **Privada** e permita o Python no firewall.
- Evite o "Encaminhar Porta" do VS Code: ele passa pelos servidores da Microsoft e deixou os comandos lentos/caindo nos testes.

No topo aparece **Online**, e a tela **Início** mostra ocupação, potência e modo da carga.

---

## 6. Roteiro de teste (e de apresentação)
| # | Ação no app | O que deve acontecer no ESP32 |
|---|---|---|
| 1 | Início: passe a mão no PIR | Em ~2–5 s a sala vira **Ocupada** e a potência vai para **1,10 kW** |
| 2 | Controle → **ON** | LED/ventoinha liga mesmo sem ninguém; OLED `Modo:ON` |
| 3 | Saia da frente do sensor (modo ON) | Continua ligado; aparece o alerta **"sala vazia com AC ligado"** |
| 4 | Controle → **Desligar ar-condicionado** | Desliga; OLED mostra `CORTE REALIZADO` |
| 5 | Controle → **Ligar ar-condicionado** | Volta a ligar; OLED `AC LIGADO` |
| 6 | Controle → **OFF** | Desliga mesmo com movimento |
| 7 | Controle → **AUTO** | Volta a seguir o sensor (liga com movimento, desliga 30 s depois) |
| 8 | Controle → mensagem "Bem-vindos!" → Enviar | Aparece na última linha do OLED (texto longo rola) |
| 9 | Tire o ESP32 da tomada | Em ~15 s o app mostra **Dispositivo offline** |
| 10 | Ligue de novo | Reconecta sozinho e **recupera o último comando** |
| 11 | http://localhost:8000/banco | Tabelas do banco com as leituras e os comandos gravados (atualiza sozinha) |
| 12 | http://localhost:8000/docs | Swagger com todas as rotas (bom para mostrar a API) |

> A potência é **simulada**: 1100 W com a ventoinha ligada, 0 W desligada (`POTENCIA_AC_W` no firmware). O consumo acumulado (kWh) é calculado pelo back-end.

---

## 7. Plano B: sem a placa
Se o ESP32 der problema na hora, com o back-end rodando, abra **outro** terminal:
```powershell
cd src\backend
.venv\Scripts\activate
python ..\hardware\simulador_esp32.py
```
Ele faz o mesmo que o ESP32 (mesmos tópicos MQTT). Digite `p` + Enter = movimento no sensor; `o` = presença contínua; `q` = sair.
Não rode o simulador e o ESP32 real **ao mesmo tempo** (os dois falam como "Sala 101").

---

## 8. Quando o módulo relé chegar
1. **Mude o LED do GPIO 18 para o GPIO 23** (vira a "luz da sala": acende sozinho com presença).
   IN1 → GPIO 18 (ventoinha 1), IN2 → GPIO 19 (ventoinha 2), VCC → VIN (5 V), GND → GND.
2. Ventoinha: **+ da fonte → COM**, **NO → + da ventoinha**, − da ventoinha direto na fonte.
3. No `main.ino`: `RELE_ATIVO_EM_LOW = true` → gravar. Se ficar invertido, volte para `false`.
4. Refaça o roteiro do item 6.

Detalhes em `src/hardware/README.md`.

---

## 9. Subir para o GitHub (quando tudo estiver ok)
Na pasta do projeto:
```powershell
git status
git add -A
git commit -m "Integra front-end, back-end FastAPI e firmware ESP32 via MQTT"
git push
```
O que entra nesse commit:
- `src/frontend/`: versão nova do front (a que estava só no zip do Trello), apontando para o back-end.
- `src/backend/`: rotas `/telemetria`, `/comando-carga`, `/mensagem`, `/rooms/{id}/ac/on`, `/device/status`, MQTT com reconexão e testes.
- `src/hardware/`: firmware novo (Wi-Fi sem travar, PIR com tempo, relé duplo, OLED) e o simulador.
- READMEs e este passo a passo.

> Antes do commit, **apague sua senha do Wi-Fi** do `main.ino` (volte para `SUA_SENHA_WIFI`), senão ela fica pública no GitHub.
