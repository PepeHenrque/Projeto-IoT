# CampusSmart — Front-end da Sala 101

## 1. Apresentação

**CampusSmart** é a interface web de monitoramento e gerenciamento energético de **um único ambiente: a Sala 101**.

Ela mostra, em tempo real, ocupação, temperatura, umidade, **potência atual (W)** e **consumo acumulado (kWh)**, gera alertas de desperdício e permite:
- ligar e desligar o **ar-condicionado** (o único equipamento controlado pela interface);
- escolher o modo da carga controlada (**ON / OFF / AUTO**);
- enviar uma mensagem ao **display OLED** da sala.

**Objetivo:** identificar e evitar desperdício de energia (por exemplo, ar-condicionado ligado com a sala vazia).

A Sala 101 é fixa: não há lista, busca, filtro, seleção nem cadastro de salas. O número da sala está em `js/config.js` (`ROOM_ID: 101`).

> Este README trata somente do **front-end**. ESP32, hardware, display físico e o fluxo do Node-RED são responsabilidade dos demais integrantes da equipe.

> **Integração com o back-end (18/11):** por padrão o front agora conversa com o **back-end FastAPI** (`src/backend`), que tem as mesmas rotas usadas aqui (`/api/v1/telemetria`, `/comando-carga`, `/mensagem`, `/rooms/101/ac/on|cut`) e repassa os comandos ao ESP32 via MQTT. O próprio back-end serve esta interface em **http://localhost:8000/**. O fluxo do Node-RED continua disponível como simulador: abra `index.html?api=http://localhost:1880`. A única mudança de código foi o `API_BASE` em `js/config.js` (e textos de tela que citavam o Node-RED).

## 2. Tecnologias

| Tecnologia | Uso neste projeto |
|---|---|
| **HTML5** | Página única (`index.html`): barra superior, área das telas, menu inferior e modal. |
| **CSS3** | Visual e responsividade (`css/style.css`): Grid, Flexbox, variáveis CSS e *media queries*. |
| **JavaScript puro (ES2020)** | Toda a lógica. Sem frameworks, sem *build* e sem módulos ES; os arquivos são carregados por `<script>` em ordem. |
| **Fetch API** | Única forma de falar com a API (telemetria e comandos), com `AbortController` para *timeout*. |
| **Roteamento por hash** | Troca de tela sem recarregar (`#/inicio`, `#/controle`, `#/alertas`, `#/historico`). |
| **SVG** | Gráfico de potência (últimas leituras) no Dashboard. |
| **Playwright + Python / Node** | Apenas para os testes automatizados (`tests/`). Não fazem parte da interface. |

## 3. Estrutura de pastas

```
CampusSmart/
├── index.html                      Estrutura das telas e ordem de carregamento dos scripts
├── css/style.css                   Estilos e responsividade
├── js/
│   ├── config.js                   ÚNICO lugar com endereço da API, endpoints, intervalos e limites
│   ├── app.js                      Inicialização: roteador, menu, indicador de conexão, cliques (data-action)
│   ├── services/
│   │   ├── http.js                 ÚNICO fetch(): timeout, formato do corpo, erros tipados
│   │   ├── campusApi.js            Consultas, comandos, validação da mensagem OLED e leitura tolerante da telemetria
│   │   └── historyService.js       Histórico da sessão (em memória)
│   ├── core/
│   │   ├── store.js                Estado único da aplicação
│   │   ├── telemetry.js            Atualização automática (polling) da telemetria
│   │   ├── actions.js              Comandos do usuário (confirmação → envio → resultado)
│   │   ├── selectors.js            Estados derivados (equipamento, contadores)
│   │   └── alerts.js               Regras de alerta de desperdício
│   ├── views/
│   │   ├── dashboard.js            Tela Início
│   │   ├── control.js              Tela Controle
│   │   ├── alerts.js               Tela Alertas
│   │   ├── history.js              Tela Histórico
│   │   └── shared.js               Formatadores e peças reutilizadas (W/kW, kWh, selos de estado)
│   ├── ui/
│   │   ├── html.js                 Helpers de marcação (com escape de texto)
│   │   └── modal.js                Modal de confirmação / carregando / sucesso / erro
│   ├── data/roomProfile.js         Perfil da Sala 101 e do ar-condicionado
│   └── dev/mockServer.js           SIMULAÇÃO da API, só com ?mock=... na URL
├── node-red/                       Fluxo de referência usado nos testes (JSON importável) e patch do AC
├── tests/                          Testes automatizados
└── docs/                           Relatório de testes e lista de problemas corrigidos
```

**Regra de organização:** as telas (`views/`) nunca chamam `fetch` nem conhecem URLs; usam `store`, `selectors` e `actions`. Só `services/` fala com o exterior (verificado por `tests/structure.test.py`).

## 4. Telas

O menu inferior tem 4 telas.

### Início (Dashboard)
- "Sala 101" e selo **Ocupada / Vazia** (ou "Ocupação não informada").
- **Potência atual:** abaixo de 1000 W aparece em **W** (ex.: `350 W`); a partir de 1000 W, em **kW** (ex.: `1,55 kW`), com o valor em W abaixo.
- **Consumo acumulado** em **kWh** (ex.: `12,34 kWh`). Potência e energia são indicadores separados.
- Linha "Carga: energizada/cortada · modo ON/OFF/AUTO".
- **Gráfico** com as últimas leituras de potência.
- **Ambiente:** temperatura (°C) e umidade (%).
- **Ar-condicionado:** estado atual (Ligado, Desligado, Sem alimentação, Não informado ou Sem comunicação).
- **Alertas de desperdício** mais importantes.
- Hora da última atualização; os valores ficam esmaecidos quando estão desatualizados.
- Campo ausente na telemetria = **"Não informado pela telemetria"**. Nenhum número é inventado.

### Controle
- **Ar-condicionado:** botão **"Ligar ar-condicionado"** ou **"Desligar ar-condicionado"**, conforme o estado real lido da telemetria. Sempre pede confirmação. O botão só aparece quando a API informa o estado do equipamento.
- **Modo da carga:** botões **ON** (carga ligada), **OFF** (carga cortada) e **AUTO** (a lógica automática decide). Mostram o modo atual e o estado real da carga, lidos da telemetria.
- **Display OLED:** campo de texto com contador (até **64** caracteres) e botão "Enviar ao display".
  - O botão fica desabilitado com o campo vazio ou só com espaços.
  - O texto é validado antes do envio (vazio ou acima do limite → "Mensagem inválida"; nada é enviado).
  - O sucesso só aparece depois de uma resposta 2xx e diz exatamente o que foi confirmado: **o Node-RED recebeu a mensagem**. A API atual não informa se o display físico a exibiu, e a interface não afirma isso.

### Alertas
Cada alerta mostra equipamento, motivo, tipo de desperdício, prioridade e "Ativo desde HH:MM", com atalho para o Controle. Regras em `js/core/alerts.js`:
- sala vazia + ar-condicionado ligado e energizado → **Alta**;
- potência acima de `ALERTS.HIGH_POWER_W` (2000 W, em `config.js`) → **Baixa**.

Ar-condicionado "ligado" com a carga cortada **não** gera alerta, pois não está consumindo. Sem telemetria, a tela mostra erro e nunca afirma "sem alertas".

### Histórico
Leituras de consumo, mudanças de estado (ocupação, ar-condicionado, modo da carga) e comandos enviados, com horário e resultado. **São apenas os registros desta sessão**, guardados na memória do navegador; somem ao recarregar a página, e a tela avisa isso.

## 5. Comunicação com o Node-RED

Toda a comunicação passa por **um único `fetch()`** (`js/services/http.js`), chamado pelas funções de `js/services/campusApi.js`. O endereço base está em `API_BASE` e os caminhos em `CampusSmart.endpoints` (`js/config.js`).

`http.js` usa *timeout* de 8 s e converte falhas em erros tipados: `timeout`, `network`, `offline` (HTTP 503) e `http` (outros códigos). Quando a API devolve um motivo (ex.: `{"erro":"..."}`), ele aparece na mensagem de erro.

### Formato dos POST

O corpo é enviado como **formulário** (`Content-Type: application/x-www-form-urlencoded;charset=UTF-8`), por exemplo `mensagem=Ol%C3%A1`.

- O navegador trata isso como requisição "simples": **não há preflight `OPTIONS`** (o Node-RED não tem nó OPTIONS).
- O nó **http in** do Node-RED converte esse formato em objeto: `msg.payload = { mensagem: "Olá" }`. Assim, uma função que lê `msg.payload.mensagem` ou `msg.payload.comando` funciona diretamente.
- Os valores chegam como texto (ex.: `room_id` chega como `"101"`).
- Alternativa: `?simple=0` (ou `SIMPLE_REQUESTS: false`) envia `application/json`, que exige `httpNodeCors` habilitado no `settings.js` do Node-RED.

### Endpoints utilizados

| Método | Endpoint | Finalidade | Campos enviados |
|---|---|---|---|
| GET | `/api/v1/telemetria` | Telemetria, a cada 5 s | — |
| POST | `/api/v1/rooms/101/ac/on` | Ligar o ar-condicionado | `room_id=101` |
| POST | `/api/v1/rooms/101/ac/cut` | Desligar o ar-condicionado | `room_id=101` |
| POST | `/api/v1/comando-carga` | Modo da carga | `comando=ON` (ou `OFF`, `AUTO`) |
| POST | `/api/v1/mensagem` | Mensagem ao display OLED | `mensagem=texto` (1 a 64 caracteres) |

### Telemetria lida pela interface
```json
{ "sala":101, "timestamp":"2026-11-17T02:29:02Z", "ocupada":false, "temperatura":23.9, "umidade":56,
  "potencia_w":1542, "energia_kwh":12.3404, "ac":{"ligado":true}, "carga":{"modo":"ON","ligada":true} }
```
- `potencia_w` → Potência atual; `energia_kwh` → Consumo acumulado; `ac.ligado` → estado do ar-condicionado; `carga.ligada` → estado real da carga.
- `campusApi.js` também entende outros nomes e unidades (ex.: `potencia_kw`, `energia_wh`, `consumo_kwh`, texto com vírgula, ou o grupo `consumo: {…}`) e converte para W e kWh.
- Outros campos que a telemetria trouxer são ignorados pela interface.
- Para conferir o que chegou, digite `CampusSmart.lastRawTelemetry` no console do navegador (F12).

### Pontos de integração para um back-end futuro
Nenhum back-end ou banco de dados foi implementado e não há endpoints fictícios. Para adaptar o front-end a uma API própria, só estes pontos mudam (marcados com `[BACKEND]` no código):
1. `js/config.js`: `API_BASE` e `CS.endpoints`.
2. `js/services/http.js`: autenticação, se existir.
3. `js/services/campusApi.js`: `normalizeTelemetry`, `EQUIPMENT_ROUTES` e `getRoomProfile`.
4. `js/services/historyService.js`: fonte do histórico persistente.

As telas não precisam ser reescritas.

## 6. Interações e estados

- **Botões de comando** ficam desabilitados enquanto há um comando em andamento (evita envio duplo).
- **Confirmação:** ligar/desligar o ar-condicionado pergunta "Tem certeza…?" com Cancelar / Ligar ou Desligar. Cancelar não envia nada.
- **Carregando:** *spinner* enquanto a API responde; não fecha com Esc nem com clique fora.
- **Sucesso:** só após resposta 2xx. A telemetria é relida em seguida.
- **Erro:** mensagem específica, com **Fechar** e **Tentar novamente**:
  - 503 → "Dispositivo offline";
  - *timeout* → "Tempo esgotado";
  - rede → "Sem conexão";
  - outros códigos → "O servidor recusou a requisição (código N)", seguido do motivo informado pelo servidor, quando houver;
  - texto do OLED inválido → "Mensagem inválida" (só **Fechar**, pois repetir não resolveria).
- **Conexão:** selo no topo: *Conectando…*, *Online*, *Dispositivo offline* (503) ou *Sem conexão*.
- **Atualização automática:** a cada 5 s (`POLL_MS`); pausa com a aba oculta e retoma ao voltar. Com a API fora, mantém a última leitura marcada como desatualizada.
- **Acessibilidade:** `aria-pressed` nos modos, `role="status"`/`alert` nos estados, foco no modal, alvos de toque ≥ 44 px.

## 7. Responsividade

- **Celulares (até ~430 px):** largura total, menu fixo no rodapé, áreas seguras (`env(safe-area-inset-*)`). Abaixo de 340 px, fontes e espaçamentos diminuem.
- **Tablets e computadores (≥ 600 px):** coluna centralizada de até 430 px; o modal vira uma caixa centralizada.
- O campo do OLED usa fonte de 16 px para evitar zoom no iOS.

## 8. Como executar

1. Abra a pasta `CampusSmart` no **VS Code**.
2. Botão direito em `index.html` → **Open with Live Server** (porta 5500). Sem Live Server: `python3 -m http.server 5500` na pasta do projeto.
3. Acesse `http://127.0.0.1:5500/index.html`.
4. **Endereço da API:** o padrão é `http://localhost:1880` (Node-RED). Para outro endereço (ex.: acessar do celular), edite `API_BASE` em `js/config.js`.
5. O selo do topo deve ficar **Online** e a hora em "Atualizado" deve mudar a cada 5 s.

### Simulação (sem Node-RED)
`index.html?mock=1` ativa uma **API simulada dentro do navegador** (`js/dev/mockServer.js`). Nesse modo:
- uma faixa amarela **"SIMULAÇÃO"** fica visível no topo;
- **nada** é enviado ao Node-RED, ao ESP32 ou ao display;
- o sucesso do OLED diz explicitamente que foi uma simulação.

Variações: `?mock=503` (comandos retornam 503), `?mock=cmdnet` (comandos sem rede), `?mock=down` (tudo fora), `?mock=slow` (comandos demoram 3 s), `?mock=noac` (telemetria sem o ar-condicionado), `?mock=nopower` (sem potência/energia), `?mock=altnames` (potência em kW e energia em Wh).

Sem `?mock`, o arquivo de simulação não faz nada: para remover a simulação definitivamente, apague `js/dev/mockServer.js` e a linha correspondente no `index.html`.

## 9. Testes

```bash
pip install playwright && playwright install chromium
bash tests/run_all.sh                                   # emulador do Node-RED + Chromium
NODERED_DIR=/caminho/node-red bash tests/run_all.sh     # inclui a suíte com Node-RED real
```

| Suíte | Cobre |
|---|---|
| `structure.test.py` | Sala 101 exclusiva, ar-condicionado como único equipamento, camadas, endpoints reais, pontos `[BACKEND]`, formato dos POST |
| `flow_http.test.py` | Rotas do fluxo, CORS, 400/404/503, formato de formulário, modos ON/OFF/AUTO, reprodução e correção do erro 400 do OLED |
| `browser_cors.test.py` | CORS no Chromium real e envio ao OLED com dois tipos de fluxo |
| `app.test.py` | Dashboard, telemetria, ar-condicionado, modos, OLED, modais, erros, alertas, histórico, navegação e responsividade |
| `realnodered.test.py` | Chromium real contra Node-RED real |

Resultados da última execução: `docs/relatorio-de-testes.md`.

**Limitações:**
- Sem o dispositivo físico, o OLED foi testado até o Node-RED (resposta 200 com o texto recebido). A exibição no display real depende do fluxo e do hardware da equipe.
- O fluxo em `node-red/` é uma referência com sensores e atuadores simulados. O fluxo em uso pela equipe pode ser diferente.
- Responsividade testada em viewports emulados no Chromium, não em aparelhos físicos nem em Firefox/Safari.
