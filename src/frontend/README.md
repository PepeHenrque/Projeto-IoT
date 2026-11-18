# CampusSmart — Sala 101

Monitoramento e controle de energia dedicados **exclusivamente à Sala 101**. HTML + CSS + JavaScript puros (sem build, sem módulos ES: funciona no Live Server e abrindo o `index.html`). Integrado ao Node-RED; pronto para receber back-end e banco de dados no futuro.

Telas (menu inferior): **Início** (dashboard) · **Controle** · **Alertas** · **Histórico**.

## 1. Como executar
1. **Node-RED:** apague a aba antiga "CampusSmart API" (rotas duplicadas dão conflito), importe `node-red/campussmart-flow.json` e clique em **Deploy**.
2. Abra `index.html` com o **Live Server** (`http://127.0.0.1:5500`). O Node-RED é esperado em `http://localhost:1880` (`js/config.js` → `API_BASE`).
3. Sem Node-RED? `index.html?mock=1` usa uma API simulada no navegador. Variações: `?mock=503` (comandos → 503), `?mock=cmdnet` (comandos sem rede), `?mock=down` (tudo fora), `?mock=slow` (comandos demoram 3 s), `?mock=noluz` (telemetria sem iluminação).

## 2. O que cada tela faz
| Tela | Conteúdo |
|---|---|
| **Início** | Identificação da Sala 101, ocupação (Ocupada/Vazia), temperatura, umidade, potência e energia em tempo real, estado da iluminação e do ar-condicionado, indicador "N de M equipamentos ligados", alertas de desperdício. |
| **Controle** | Liga/desliga **ar-condicionado** e **iluminação** (cada um mostra o estado real: verde = ligado, cinza = desligado, vermelho = sem comunicação, laranja = não informado); **Modo da carga ON / OFF / AUTO**; mensagem ao **display OLED**. |
| **Alertas** | Equipamento, motivo, tipo de desperdício, prioridade (Alta/Média/Baixa) e estado (Ativo desde HH:MM). Sem desperdícios: "Nenhum desperdício identificado". |
| **Histórico** | Consumo, alterações de estado e comandos enviados, com horário (veja 6). |

Todo comando segue o mesmo padrão: **confirmação → carregando → sucesso → (erro com "Tentar novamente")**. O sucesso só aparece **depois** que o Node-RED responde 2xx; nada é simulado.

Regras de alerta (`js/core/alerts.js`, ajustáveis): sala **vazia** + ar-condicionado ligado = **Alta**; sala vazia + iluminação ligada = **Média**; potência acima de `ALERTS.HIGH_POWER_W` (2000 W, em `config.js`) = **Baixa** ("consumo acima do padrão"). Sem telemetria não se afirma nada: a tela mostra erro/aviso, nunca "sem alertas".

## 3. Endpoints do Node-RED
| Método | Rota | Uso |
|---|---|---|
| GET | `/api/v1/telemetria` | telemetria (a cada 5 s) |
| POST | `/api/v1/rooms/:room_id/ac/cut` | desliga o ar-condicionado |
| POST | `/api/v1/rooms/:room_id/ac/on` | liga o ar-condicionado |
| POST | `/api/v1/rooms/:room_id/light/on` | liga a iluminação (**novo**) |
| POST | `/api/v1/rooms/:room_id/light/off` | desliga a iluminação (**novo**) |
| POST | `/api/v1/comando-carga` | `{"comando":"ON\|OFF\|AUTO"}` |
| POST | `/api/v1/mensagem` | `{"mensagem":"texto"}` (até 64 caracteres) |

Todas só aceitam `room_id = 101` (404 para outro). Resposta `503` = dispositivo offline.

Formato da telemetria esperado (campo ausente = "Não informado" e controle desabilitado):
```json
{ "timestamp":"2026-11-16T10:30:00Z", "ocupada":false, "temperatura":24.2, "umidade":56,
  "potencia_w":1404, "energia_kwh":12.34,
  "ac":{"ligado":true}, "iluminacao":{"ligada":true}, "carga":{"modo":"AUTO"} }
```

### 3.1 O que mudou no Node-RED nesta etapa
- **Novas rotas** `light/on` e `light/off` e o campo `iluminacao` na telemetria (não existia nada de iluminação). A iluminação é simulada dentro do fluxo, como o AC, e a potência reage a ela. `ac/cut`, `ac/on`, `comando-carga`, `mensagem` e o CORS **não foram alterados**.
- **Se você usa um fluxo próprio:** importe só os patches (3 nós por rota, com CORS embutido) e **troque a linha de estado pelo seu atuador real**: `node-red/patch-ac-on.json` e `node-red/patch-iluminacao.json`. Lembre de devolver `iluminacao:{ligada:true|false}` na telemetria, senão a interface mostra "Não informado".

### 3.2 CORS (correção preservada)
O nó HTTP In **não aceita OPTIONS**, então nós "OPTIONS" nunca funcionaram. Solução vigente: (a) todas as respostas passam por **um único nó de CORS** e **uma única** resposta HTTP; origens em `CORS_ORIGINS` (variável da aba, padrão `http://127.0.0.1:5500,http://localhost:5500`); (b) o front envia o POST como `text/plain` (requisição simples, **sem preflight**; `SIMPLE_REQUESTS` em `config.js`). Para JSON com preflight habilite `httpNodeCors` no `settings.js` e use `SIMPLE_REQUESTS:false`:
```js
httpNodeCors: { origin: ["http://127.0.0.1:5500","http://localhost:5500"], methods: "GET,POST,OPTIONS", allowedHeaders: "Content-Type, Accept", maxAge: 600 },
```
Teste de falhas reais: nos nós *inject* do fluxo, "Alternar dispositivo offline (503)" e "Alternar sala ocupada/vazia".

## 4. Organização do código
```
index.html, style.css
js/config.js                 ÚNICO lugar com URLs, intervalos, limites e fontes de dados
js/services/http.js          ÚNICO fetch() (timeout, erros tipados, CORS simples)
js/services/campusApi.js     serviço do Node-RED: getTelemetria, setEquipment, sendLoadCommand, sendOledMessage, getRoomProfile
js/services/historyService.js  histórico (fonte 'session' hoje, 'api' no futuro)
js/data/roomProfile.js       perfil da Sala 101 e seus equipamentos (futuro: vem do back-end/banco)
js/core/                     alerts (regras puras), store, selectors, telemetry (polling), actions (comandos)
js/ui/                       html (helpers) e modal (confirmação/carregando/sucesso/erro)
js/views/                    dashboard, control, alerts, history (+ shared)
js/dev/mockServer.js         API falsa só para desenvolvimento
js/app.js                    roteador por hash + bootstrap
node-red/                    campussmart-flow.json + patches
tests/                       bateria automatizada (+ emulador do Node-RED)
```
Regras (verificadas por `tests/structure.test.py`): views não chamam `fetch`, não conhecem URLs e falam com `store`/`selectors`/`actions`; só `services/` fala com o exterior.

Para **adicionar um equipamento**: um item em `js/data/roomProfile.js`, uma linha em `EQUIPMENT_ROUTES` (`campusApi.js`) e a rota no Node-RED. As telas se adaptam sozinhas.

## 5. Preparação para back-end e banco de dados (nada implementado)
O back-end futuro intermedia aplicativo ↔ Node-RED ↔ banco. Para ligá-lo, só `config.js` e `services/` mudam; **telas e regras ficam**.

| Necessidade | Ponto de integração no front | Situação |
|---|---|---|
| Informações da Sala 101, sensores e equipamentos | `api.getRoomProfile()` + `js/data/roomProfile.js` | local; trocar por chamada ao back-end |
| Telemetria / estados dos dispositivos | `api.getTelemetria()`, `normalizeTelemetry` | real (Node-RED); apontar `API_BASE` ao back-end |
| Comandos (iluminação, climatização) | `api.setEquipment()`, `EQUIPMENT_ROUTES` | real (Node-RED) |
| Histórico de comandos/ações | `history.recordCommand()` | sessão hoje; com `HISTORY_SOURCE:'api'` o back-end registra |
| Histórico de consumo e de funcionamento | `history.recordTelemetry()` | idem |
| Alertas | `core/alerts.js` (derivação local) | trocar por `api.getAlerts()` no serviço e em `selectors.alerts` |

Contrato **proposto** para o histórico (não existe ainda; implementado no front só para `HISTORY_SOURCE:'api'`, **não testado** por falta de servidor):
`GET /api/v1/rooms/101/history/consumption → [{ts, potencia, energia}]`, `…/history/states → [{ts, equip, from, to}]`, `…/history/commands → [{ts, label, status, detail}]`.

Mapa para o banco (tecnologia **não escolhida**): sala e equipamentos ← `roomProfile`; consumo ← `telemetry.potencia/energia`; estados ← `acLigado, luzLigada, ocupada, modoCarga`; alertas ← `core/alerts.js` (id, nível, tipo, equipamento, desde); comandos ← `core/actions.js`.

### Como substituir dados locais por reais
1. Implemente no back-end os endpoints necessários, com CORS para a origem do front.
2. `config.js`: `API_BASE` = endereço do back-end; `HISTORY_SOURCE:'api'` se ele fornecer histórico.
3. `campusApi.js`: ajuste `getRoomProfile`, `EQUIPMENT_ROUTES` e `normalizeTelemetry` aos nomes reais.
4. Remova `js/dev/mockServer.js` (e a tag `<script>`) quando não precisar mais.

## 6. Histórico: o que existe hoje
Mostra **somente o que o próprio navegador observou/enviou nesta sessão**, em memória: leituras de consumo, mudanças de estado detectadas entre leituras e comandos enviados (sucesso/erro). Some ao recarregar a página, e a tela avisa isso. Nada é inventado; o histórico persistente depende do back-end/banco.

## 7. Testes
```bash
pip install playwright && playwright install chromium
bash tests/run_all.sh
```
| Suíte | Verif. | Cobre |
|---|---|---|
| `structure.test.py` | 15 | Sala 101 exclusiva (sem outras salas), camadas, scripts, sem módulos ES |
| `flow_http.test.py` | 60 | 7 rotas, CORS em GET/POST/erros, OPTIONS com e sem `httpNodeCors`, 400/404/503, ciclo ligar/desligar AC e iluminação, patches, sem resposta duplicada |
| `browser_cors.test.py` | 18 | **Chromium real**, origens `127.0.0.1:5500 → localhost:1880`: reprodução do erro original (`tests/fixtures`), correção, JSON com preflight |
| `app.test.py` | 93 | dashboard, telemetria, ligar/desligar AC e iluminação, modo ON/OFF/AUTO, OLED, atualização após comandos, erros 503/rede com "Tentar novamente", carregando/vazio/sem comunicação, alertas, histórico, navegação, ausência de outras salas, 4 tamanhos de celular |

### Limitações (leia)
- **Sem Node-RED instalado no ambiente de teste.** Os testes usam `tests/nodered-emulator.js`, que executa o **JSON real do fluxo** e reproduz o comportamento do HTTP In (inclusive o erro original). Falta a confirmação no **seu** Node-RED: importe o fluxo e comande o AC e a iluminação pela interface.
- A **iluminação real** depende do seu hardware: as rotas `light/*` e o campo `iluminacao` foram criados como simulação no fluxo. Se o seu Node-RED não os tiver, a interface mostra "Não informado" e desabilita o controle (comportamento testado).
- "Modo automático" = **Modo da carga AUTO** (único modo automático que a API possui). Não existe modo automático por equipamento.
- A tela "Fluxo" (user flow multi-sala) foi removida junto com a lista de salas.
- Limite de consumo (2000 W) e prioridades dos alertas são regras minhas, ajustáveis em `config.js` e `roomProfile.js`.
