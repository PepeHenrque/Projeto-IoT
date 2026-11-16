# CampusSmart — primeira versão da interface

## Como executar
1. Extraia o ZIP.
2. Abra a pasta `CampusSmart` no VS Code.
3. Abra `index.html` no navegador (ou use a extensão Live Server).

## O que já funciona
- Navegação entre Início, Salas, Alertas e Fluxo.
- Busca e filtros de salas.
- Visualização dos detalhes de uma sala.
- Modal de confirmação para desligar equipamentos.
- Atualização visual do estado do equipamento e remoção dos alertas relacionados.

## Importante
Esta versão usa dados simulados no JavaScript. Ainda não está conectada ao Node-RED nem a sensores físicos. Na próxima etapa vamos criar os endpoints no Node-RED e trocar a simulação por chamadas `fetch()`.

## Estrutura
- `index.html`: estrutura das telas.
- `style.css`: identidade visual e responsividade.
- `app.js`: dados simulados e interações.
