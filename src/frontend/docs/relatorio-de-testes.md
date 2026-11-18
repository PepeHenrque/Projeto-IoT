# Relatório de testes — CampusSmart (Sala 101)

Data: 17/11/2026. Resultado: **277/277 verificações aprovadas** em uma execução de `bash tests/run_all.sh`, com `NODERED_DIR` apontando para um **Node-RED 5.0.10 real**.

| Suíte | Resultado |
|---|---|
| `structure.test.py` | 25/25 |
| `flow_http.test.py` | 67/67 |
| `browser_cors.test.py` | 24/24 |
| `app.test.py` | 133/133 |
| `realnodered.test.py` (Node-RED real + Chromium real) | 28/28 |

## Ambiente e limites
- Node-RED real 5.0.10 com o fluxo de referência `node-red/campussmart-flow.json` (sensores e atuadores **simulados** no próprio fluxo). **Não houve hardware físico**: o display OLED foi testado até o Node-RED, não até a tela física.
- Navegador: Chromium (Playwright). Firefox, Safari e aparelhos físicos **não** foram testados.
- `flow_http`, `browser_cors` e `app` usam um emulador que executa o JSON real do fluxo e trata o corpo como o Node-RED (formulário → objeto; `text/*` → texto). `realnodered` usa o Node-RED de verdade.

## Testes obrigatórios

| Teste | Resultado | Suítes |
|---|---|---|
| Carregamento do Dashboard | Aprovado: Sala 101, ocupação, potência, consumo, gráfico, temperatura, umidade, ar-condicionado e alertas | app, realnodered |
| Atualização da telemetria | Aprovado: novas leituras chegam sozinhas (polling de 5 s); o consumo acumulado aumenta | app, realnodered |
| Ligar o ar-condicionado | Aprovado: POST `ac/on`, Node-RED confirma `ac.ligado = true`, tela mostra "Ligado" | flow_http, app, realnodered |
| Desligar o ar-condicionado | Aprovado: POST `ac/cut`, Node-RED confirma `ac.ligado = false`, tela mostra "Desligado" e o alerta some | flow_http, app, realnodered |
| Envio de mensagem ao OLED | Aprovado: texto com acentos e símbolos chega idêntico ao Node-RED; validação de vazio e de 64 caracteres; erros 400, 503 e rede mostrados com clareza | flow_http, browser_cors, app, realnodered |
| Iluminação removida | Aprovado: nenhuma referência no código, HTML, CSS, README nem no texto das 4 telas | structure, app |
| Sem referências a múltiplas salas | Aprovado: sem lista, busca, filtro, seleção ou cadastro de salas; rotas antigas caem no Dashboard | structure, app |

## Erro 400 do OLED: reprodução e correção
1. **Reprodução** (Node-RED real + Chromium, código anterior): com um fluxo cuja função lê `msg.payload.mensagem` diretamente, o envio mostrou exatamente *"Não foi possível executar o comando. O servidor recusou a requisição (código 400)."*; a resposta do Node-RED foi `{"erro":"mensagem vazia ou maior que 64 caracteres"}`.
2. **Correção** (mesmo fluxo, mesmo Node-RED, código novo): resposta 200 com o texto exato. Também testado com o fluxo de referência do projeto: 200.
3. Os dois cenários estão automatizados em `flow_http.test.py` e `browser_cors.test.py`.

## Simulação
- Com `?mock=...`, a faixa "SIMULAÇÃO" aparece e o sucesso do OLED diz que nada foi enviado ao display (verificado em `app.test.py`).
- Sem `?mock`, a faixa não existe e todas as chamadas vão para a API real.
