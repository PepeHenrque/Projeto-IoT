# CampusSmart — Back-end (FastAPI)

API REST para o monitoramento e automação de ar-condicionado do CampusSmart.
Nesta etapa os dados são simulados em memória (`app/mock_db.py`), espelhando o `app.js`.

## Estrutura
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py        # servidor FastAPI, CORS e rotas
│   ├── schemas.py     # modelos Pydantic (contrato da API)
│   └── mock_db.py     # dados simulados + regras (trocar por BD/Node-RED depois)
├── tests/test_api.py
├── docs/exemplo_fetch_app.js
├── requirements.txt / requirements-dev.txt
└── README.md
```

## Como rodar
Requer Python 3.10+.
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
- Swagger (testar as rotas): http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

## Endpoints (`/api/v1`)
| Método | Rota | Descrição |
|---|---|---|
| GET | `/rooms` | Listar salas (filtros: `occupied`, `has_alerts`, `q`) |
| GET | `/rooms/{room_id}` | Detalhe de uma sala |
| GET | `/alerts` | Buscar alertas (filtros: `level`, `room_id`) |
| POST | `/rooms/{room_id}/ac/cut` | Comando de corte: desliga o AC e resolve os alertas dele |

Erros do comando de corte: `404` sala inexistente · `409` AC já desligado · `422` sala sem AC · `503` falha simulada (`?simulate_error=true`, útil para testar o modal de erro).

## Testes
```bash
pip install -r requirements-dev.txt
pytest
```

## CORS
Por padrão aceita qualquer origem (dev). Para restringir: `CORS_ORIGINS="http://127.0.0.1:5500" uvicorn app.main:app`.
