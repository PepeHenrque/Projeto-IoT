# CampusSmart — Back-end (FastAPI)

API REST para o monitoramento e automação de ar-condicionado do CampusSmart.
Nesta etapa os dados são simulados em memória (`app/mock_db.py`), espelhando o `app.js` e integrados com o broker MQTT para comandos e telemetria do ESP32.

## Estrutura
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py        # servidor FastAPI, CORS, MQTT e rotas
│   ├── schemas.py     # modelos Pydantic (contrato da API)
│   └── mock_db.py     # dados simulados + regras de negócio
├── tests/test_api.py  # suíte de testes com pytest
├── requirements.txt / requirements-dev.txt
└── README.md
```

## Como rodar
Requer Python 3.10+.
```bash
cd src/backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Swagger (documentação interativa): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Endpoints (`/api/v1`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/rooms` | Listar salas (filtros: `occupied`, `has_alerts`, `q`) |
| GET | `/rooms/{room_id}` | Detalhes de uma sala |
| GET | `/rooms/analytics/energy-saving` | Estatísticas de economia e desperdício de energia |
| GET | `/alerts` | Buscar alertas (filtros: `level`, `room_id`) |
| GET | `/alerts/critical/summary` | Resumo de alertas críticos pendentes |
| POST | `/rooms/{room_id}/ac/cut` | Dispara comando de corte (desliga o AC, resolve alertas e publica no MQTT) |

Erros do comando de corte: `404` sala inexistente · `409` AC já desligado · `422` sala sem AC · `503` falha simulada (`?simulate_error=true`, útil para testar o modal de erro).

## Testes
```bash
pip install -r requirements-dev.txt
pytest
```

## CORS
Por padrão aceita qualquer origem (desenvolvimento). Para restringir: `CORS_ORIGINS="http://127.0.0.1:5500" uvicorn app.main:app`.
