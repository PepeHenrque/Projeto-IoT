# CampusSmart — Back-end (FastAPI & Banco de Dados)

API REST para o monitoramento e automação de ar-condicionado do CampusSmart.
Integrada ao banco de dados relacional MySQL (tabelas `salas`, `telemetrias` e `avisos_oled`) com fallback resiliente para SQLite e comunicação MQTT em tempo real.

## Estrutura
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py        # servidor FastAPI, CORS, MQTT e rotas REST
│   ├── database.py    # conexão SQLAlchemy com MySQL / SQLite Fallback e modelos
│   ├── schemas.py     # modelos Pydantic (contrato da API)
│   └── mock_db.py     # repositório integrado ao banco relacional + regras de negócio
├── tests/test_api.py  # suíte de testes automatizados com pytest
├── requirements.txt / requirements-dev.txt
└── README.md
```

## Configuração do Banco de Dados (MySQL)
Por padrão, a aplicação tenta se conectar ao MySQL local:
- **Host**: `localhost:3306`
- **Banco**: `sistema_iot`
- **Usuário**: `root`
- **Senha**: `root` (ou a definida nas variáveis de ambiente)

Você pode personalizar através de variáveis de ambiente:
```bash
export DATABASE_URL="mysql+pymysql://seu_usuario:sua_senha@localhost:3306/sistema_iot"
# ou individualmente:
export MYSQL_USER="root"
export MYSQL_PASSWORD="suasenha"
export MYSQL_HOST="localhost"
export MYSQL_PORT="3306"
export MYSQL_DATABASE="sistema_iot"
```
> **Nota de Resiliência:** Se o servidor MySQL estiver parado ou inacessível no momento, a aplicação ativa automaticamente um banco SQLite local (`sistema_iot.db`) com o mesmo schema, garantindo que o sistema e os testes continuem funcionando sem falhas.

## Como rodar
Requer Python 3.10+.
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- **Interface (front-end) servida pelo próprio back-end:** http://127.0.0.1:8000/ (no celular, na mesma rede: `http://IP-DO-COMPUTADOR:8000/`)
- Swagger (documentação interativa): http://127.0.0.1:8000/docs
- Diagnóstico do ESP32 e do MQTT: http://127.0.0.1:8000/api/v1/device/status
- Health check: http://127.0.0.1:8000/health

## Endpoints (`/api/v1`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/telemetria` | Última leitura do ESP32 da Sala 101 (503 se o ESP32 parou de enviar há 15 s) |
| POST | `/comando-carga` | `comando=ON\|OFF\|AUTO` (formulário ou JSON) → publica no MQTT |
| POST | `/mensagem` | `mensagem=texto` (até 64 caracteres) → display OLED via MQTT e tabela `avisos_oled` |
| POST | `/rooms/{room_id}/ac/on` | Liga o ar-condicionado (na Sala 101 publica no MQTT) |
| GET | `/device/status` | Diagnóstico: ESP32 online? MQTT conectado? tópicos e último comando |
| GET | `/rooms` | Listar salas (filtros: `occupied`, `has_alerts`, `q`) |
| GET | `/rooms/{room_id}` | Detalhes de uma sala |
| GET | `/rooms/analytics/energy-saving` | Estatísticas de economia e desperdício de energia |
| GET | `/alerts` | Buscar alertas (filtros: `level`, `room_id`) |
| GET | `/alerts/critical/summary` | Resumo de alertas críticos pendentes |
| POST | `/rooms/{room_id}/ac/cut` | Dispara comando de corte (grava em `avisos_oled`, desliga o AC, resolve alertas e publica no MQTT) |
| GET | `/database/telemetrias` | Consulta histórico de telemetria recebido do ESP32 e gravado no banco |
| GET | `/database/avisos-oled` | Consulta histórico de avisos enviados ao display OLED |
| GET | `/database/status` | Exibe o status e o dialeto atual da conexão do banco (`mysql` ou `sqlite`) |

## MQTT (ligação com o ESP32)
| Tópico | Quem publica | Conteúdo |
|---|---|---|
| `campussmart/cs7f3a/sala101/telemetria` | ESP32 (a cada 2 s) | `{"ocupado", "modo", "ac_ligado", "carga_ligada", "potencia_w", "corrente_ma"}` |
| `campussmart/cs7f3a/sala101/comandos` | back-end (retain) | `{"modo_carga": "AUTO\|ON\|OFF", "ac": "ON\|OFF", "mensagem_web": "..."}` |
| `campussmart/cs7f3a/sala101/status` | ESP32 (Last Will) | `online` / `offline` |

Variáveis de ambiente: `MQTT_BROKER` (padrão `broker.hivemq.com`), `MQTT_PORT` (1883), `MQTT_TOPIC_BASE`, `CAMPUS_DISABLE_MQTT=1` (desliga o MQTT).
Sem a placa? Rode o simulador: `python ../hardware/simulador_esp32.py` (mesma lógica e tópicos do firmware).

## Testes
```bash
pip install -r requirements-dev.txt
pytest
```
