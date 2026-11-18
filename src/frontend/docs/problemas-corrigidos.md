# Problemas encontrados e corrigidos

| # | Problema | Causa | Correção |
|---|---|---|---|
| 1 | Modo de carga sem efeito visível | O fluxo só gravava a string do modo; ON, OFF e AUTO geravam a mesma potência e a telemetria não informava o estado real da carga | Fluxo: `carga:{modo, ligada}` com estado efetivo (ON energiza, OFF corta, AUTO segue a ocupação); a potência reage; o POST já devolve o estado. Interface: mostra o modo e o estado real |
| 2 | Equipamento "ligado" sem consumo | Não existia o conceito de carga cortada | Novo estado "Sem alimentação"; não conta como ligado nem gera alerta de desperdício |
| 3 | Consumo atual não aparecia em certos formatos | O front só lia poucos nomes de campo, sem converter unidades | Leitura tolerante (vários nomes, kW, Wh, texto com vírgula, objetos aninhados). Se faltar, mostra "Não informado pela telemetria" |
| 4 | Potência e energia pouco claras | Rótulos "Potência"/"Energia" e "1.431 W" ambíguo | Dois cartões: **Potência atual** (W/kW) e **Consumo acumulado** (kWh) |
| 5 | Consumo acumulado "saltava" | O fluxo integrava potência × tempo desde a última leitura, inclusive de horas sem consulta e de períodos offline | Intervalo limitado a 60 s e relógio atualizado quando o dispositivo está offline |
| 6 | Endpoints fictícios no front | `config.js` e `historyService.js` tinham `/history/...` e `HISTORY_SOURCE:'api'` | Removidos; histórico só da sessão; pontos `[BACKEND]` documentados |
| 7 | Endereço da API e estrutura | CSS na raiz, comentários de integração incompletos | `css/style.css`; endereço só em `config.js`; autenticação futura só em `http.js` |
| 8 | README desatualizado | Descrevia o histórico fictício, detalhes internos do Node-RED e do banco | Reescrito, somente Front-end |
| 9 | Teste antigo frágil | Lia "1.55 kW" como número | Testes atualizados e ampliados (de 93 para 118 no app; novos: fluxo, estrutura e Node-RED real) |

## Pendências e premissas
- A lógica de **AUTO** (segue a ocupação) é uma premissa minha, aplicada no fluxo simulado. Se o seu hardware usar outra regra, ajuste `cargaLigada` no fluxo.
- O modo padrão do fluxo passou de AUTO para ON (para a sala já iniciar energizada).
- Importante: reimporte `node-red/campussmart-flow.json` no seu Node-RED (apague a aba antiga antes) para que a telemetria traga `carga.ligada`.

---

# Rodada de 17/11/2026: simplificação e correção do OLED

| # | Problema | Causa | Correção |
|---|---|---|---|
| 10 | **Erro 400 ao enviar mensagem ao display OLED** | O front enviava JSON com `Content-Type: text/plain` (para evitar o preflight CORS). O nó *http in* do Node-RED entrega `text/plain` como **texto**, não como objeto. Uma função que lê `msg.payload.mensagem` recebia `undefined`, caía na própria validação e respondia 400 ("mensagem vazia ou maior que 64 caracteres"). | O front passou a enviar os POST como formulário (`application/x-www-form-urlencoded`). Continua sem preflight, e o Node-RED entrega `msg.payload` já como objeto (`{mensagem: "..."}`). Funciona com funções que leem `msg.payload.mensagem` e com o fluxo de referência. **Nenhuma alteração no Node-RED.** |
| 11 | Erro 400 sem explicação | A interface mostrava só o código | O motivo devolvido pela API (`{"erro": "..."}`) aparece no modal |
| 12 | Mensagem do OLED validada só pelo servidor | — | Validação antes do envio (vazia, só espaços, mais de 64 caracteres); nesses casos nada é enviado |
| 13 | Sucesso do OLED afirmava "enviado ao display" | A API só confirma o recebimento pelo Node-RED | Texto: "O Node-RED confirmou o recebimento… A exibição no display físico depende do dispositivo". No modo `?mock`, o texto diz SIMULAÇÃO |
| 14 | Simulação pouco visível | — | Faixa "SIMULAÇÃO" fixa no topo com `?mock=...` e campo `simulado: true` nas respostas simuladas |
| 15 | Iluminação fora do escopo | — | Removida de perfil da sala, API, configuração (endpoints `light/*`), histórico, alertas, telas, simulação, testes e README. Patch `node-red/patch-iluminacao.json` removido |
| 16 | Rótulos do AC diferentes do pedido | "Ligar climatização" / "Cortar energia da climatização" | "Ligar ar-condicionado" / "Desligar ar-condicionado" (endpoints inalterados) |
| 17 | Dashboard com contagem "N de M equipamentos" sem sentido para um único equipamento | — | Seção "Ar-condicionado" com o estado atual |
| 18 | CSS morto de telas antigas (lista de salas, fluxo, etc.) | Sobras de versões anteriores | Removido |

## Node-RED
O fluxo `node-red/campussmart-flow.json` **não foi alterado**. Ele ainda contém as rotas `light/on` e `light/off` e soma a iluminação na potência simulada; o front-end apenas não as usa. Remover isso do fluxo cabe à equipe do Node-RED, se desejar.
