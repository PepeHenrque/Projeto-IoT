/* CONFIGURAÇÃO CENTRALIZADA. Tudo que muda entre ambientes (endereço da API, intervalos, limites) fica AQUI.
   Nenhum outro arquivo deve conter URLs ou números mágicos.

   [BACKEND] PONTO DE INTEGRAÇÃO nº 1: hoje o front-end fala direto com o Node-RED.
   Quando existir um back-end próprio, basta apontar API_BASE para ele (e ajustar js/services/campusApi.js,
   se os caminhos ou nomes de campo forem diferentes). As telas não mudam. */
(function () {
  const CS = (window.CampusSmart = window.CampusSmart || {});
  const q = new URLSearchParams(location.search);

  CS.config = {
    // ENDEREÇO DA API (único lugar). [BACKEND] Agora: back-end FastAPI (src/backend), que fala com o ESP32 via MQTT
    // e grava no banco.  '' = mesma origem: o próprio FastAPI serve este front (http://localhost:8000/,
    // http://IP-DO-COMPUTADOR:8000/ no celular ou o link de "Encaminhar Porta" do VS Code).
    // Só quando aberto pelo Live Server (porta 5500) ou direto do arquivo (file://) aponta para o FastAPI local.
    // Para usar o fluxo simulado do Node-RED: index.html?api=http://localhost:1880
    API_BASE: q.get('api') || (location.protocol === 'file:' || location.port === '5500' ? 'http://localhost:8000' : ''),

    ROOM_ID: 101,            // o sistema é dedicado exclusivamente a esta sala
    POLL_MS: 5000,           // intervalo da telemetria
    TIMEOUT_MS: 8000,        // tempo máximo por requisição
    OLED_MAX: 64,            // limite de caracteres do display OLED (mesmo limite validado pelo fluxo do Node-RED)
    SPARK_POINTS: 24,        // leituras mantidas no gráfico do dashboard

    // true  = POST como application/x-www-form-urlencoded (requisição "simples": NÃO gera preflight OPTIONS, e o
    //         Node-RED entrega o corpo já como objeto em msg.payload). Detalhes em js/services/http.js.
    // false = POST como application/json (exige preflight: habilite httpNodeCors no settings.js do Node-RED
    //         ou use um back-end com CORS). Para testar: ?simple=0
    SIMPLE_REQUESTS: q.get('simple') !== '0',

    ALERTS: { HIGH_POWER_W: 2000 },   // acima disso: alerta de prioridade baixa "consumo acima do padrão"

    // Histórico desta sessão (em memória). [BACKEND] O histórico persistente virá do back-end/banco (etapa futura).
    HISTORY_MAX: 120         // máximo de registros mantidos em memória por lista
  };

  const room = id => `/api/v1/rooms/${id}`;
  CS.endpoints = {
    // ---- Endpoints REAIS do Node-RED (existem em node-red/campussmart-flow.json). Nenhum endpoint fictício. ----
    // [BACKEND] PONTO DE INTEGRAÇÃO nº 2: se o back-end usar outros caminhos, altere SOMENTE aqui.
    telemetria: '/api/v1/telemetria',                  // GET
    acCut: id => `${room(id)}/ac/cut`,                 // POST (desliga o ar-condicionado)
    acOn: id => `${room(id)}/ac/on`,                   // POST (liga o ar-condicionado)
    comandoCarga: '/api/v1/comando-carga',             // POST comando=ON|OFF|AUTO
    mensagem: '/api/v1/mensagem'                       // POST mensagem=texto (display OLED)
  };

  CS.core = CS.core || {}; CS.services = CS.services || {}; CS.data = CS.data || {}; CS.ui = CS.ui || {}; CS.views = CS.views || {};
})();
