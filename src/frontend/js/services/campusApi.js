/* CAMADA DE SERVIÇOS DA API: TUDO que a interface precisa do Node-RED (e, no futuro, do back-end) passa por aqui.
   As views NUNCA chamam fetch nem conhecem URLs; elas usam core/actions.js e core/telemetry.js, que usam este arquivo.

   [BACKEND] PONTO DE INTEGRAÇÃO nº 3 (este arquivo): para trocar o Node-RED por um back-end próprio, mantenha as
   funções públicas abaixo (getTelemetria, setEquipment, sendLoadCommand, sendOledMessage, getRoomProfile) e adapte só:
     - normalizeTelemetry()  -> nomes dos campos que o back-end devolver;
     - EQUIPMENT_ROUTES      -> caminhos dos comandos de equipamento;
     - getRoomProfile()      -> hoje local (js/data/roomProfile.js); futuro: GET da sala + equipamentos.
   Nenhuma tela precisa ser reescrita. */
(function () {
  const CS = window.CampusSmart;
  const http = CS.services.http, ep = CS.endpoints, cfg = CS.config;

  /* ---------- leitura tolerante da telemetria ---------- */
  const isObj = v => v !== null && typeof v === 'object' && !Array.isArray(v);
  const bool = v => (typeof v === 'boolean' ? v : undefined);
  const firstDefined = (...vals) => vals.find(v => v !== undefined && v !== null);

  /* Converte número ou texto ("350", "350.5", "350,5", "1.234,5", "350 W") em número; qualquer outra coisa vira null. */
  function toNumber(v) {
    if (typeof v === 'number') return isFinite(v) ? v : null;
    if (typeof v !== 'string') return null;
    let s = v.trim().replace(/\s*[kK]?[wW][hH]?$/, '');
    if (!s) return null;
    if (s.includes(',') && s.includes('.')) s = s.replace(/\./g, '').replace(',', '.');   // 1.234,5
    else if (s.includes(',')) s = s.replace(',', '.');                                      // 350,5
    const n = Number(s);
    return isFinite(n) ? n : null;
  }

  /* Nomes aceitos para cada grandeza. [nome, fator]: potência normalizada em W; energia normalizada em kWh. */
  const POWER_KEYS = [['potencia_w', 1], ['potencia_atual_w', 1], ['potencia', 1], ['potencia_atual', 1], ['potencia_instantanea', 1],
    ['consumo_w', 1], ['consumo_atual', 1], ['power_w', 1], ['power', 1], ['watts', 1], ['w', 1],
    ['potencia_kw', 1000], ['potencia_atual_kw', 1000], ['power_kw', 1000], ['kw', 1000]];
  const ENERGY_KEYS = [['energia_kwh', 1], ['consumo_kwh', 1], ['consumo_acumulado_kwh', 1], ['consumo_acumulado', 1],
    ['energia_acumulada_kwh', 1], ['energia_acumulada', 1], ['energia', 1], ['energy_kwh', 1], ['energy', 1], ['kwh', 1],
    ['energia_wh', 0.001], ['consumo_wh', 0.001], ['energy_wh', 0.001], ['wh', 0.001]];
  const CONTAINERS = ['consumo', 'medicao', 'medidor', 'metricas', 'power', 'energy'];   // objetos que podem agrupar as medidas

  /* Procura a medida em v (objeto), nos nomes aceitos; aceita também {valor, unidade}. Devolve número ou null. */
  function readMeasure(o, keys, kind) {
    for (const [k, factor] of keys) {
      let v = o[k]; if (v === undefined || v === null) continue;
      let f = factor;
      if (isObj(v)) {                                           // ex.: { valor: 1.4, unidade: "kW" }
        const unit = String(firstDefined(v.unidade, v.unit, '') || '').toLowerCase();
        v = firstDefined(v.valor, v.value);
        if (kind === 'power') f = unit.startsWith('kw') ? 1000 : 1;
        else f = unit === 'wh' ? 0.001 : 1;
      }
      const n = toNumber(v);
      if (n !== null) return n * f;
    }
    return null;
  }
  function findMeasure(root, keys, kind) {
    let n = readMeasure(root, keys, kind);
    for (const c of CONTAINERS) { if (n !== null) break; if (isObj(root[c])) n = readMeasure(root[c], keys, kind); }
    return n;
  }

  /* Converte a resposta bruta no formato interno. Campo ausente = null/undefined ("o Node-RED não informou"):
     a interface mostra "Não informado" e desabilita o controle correspondente. Nunca inventa valor. */
  function normalizeTelemetry(raw) {
    const r = isObj(raw) ? raw : {};
    const ac = r.ac || r.climatizacao || {}, carga = isObj(r.carga) ? r.carga : {};
    const ts = firstDefined(r.timestamp, r.ts);
    const modo = firstDefined(carga.modo, carga.mode, r.modo_carga, typeof r.carga === 'string' ? r.carga : undefined);
    const tsDate = ts ? new Date(ts) : new Date();
    return {
      ocupada: bool(firstDefined(r.ocupada, r.presenca, r.occupied)),
      temperatura: toNumber(firstDefined(r.temperatura, r.temp)),
      umidade: toNumber(firstDefined(r.umidade, r.humidity)),
      potencia: findMeasure(r, POWER_KEYS, 'power'),        // W   (instantânea)
      energia: findMeasure(r, ENERGY_KEYS, 'energy'),       // kWh (acumulada)
      acLigado: bool(firstDefined(ac.ligado, ac.on, ac.ativo, r.ac_ligado)),
      modoCarga: modo ? String(modo).toUpperCase() : null,
      cargaLigada: bool(firstDefined(carga.ligada, carga.ligado, carga.energizada)),   // estado EFETIVO da carga (true = energizada)
      ts: isNaN(tsDate) ? new Date() : tsDate
    };
  }

  // Rota REAL de cada equipamento (ligar / desligar). Hoje só o ar-condicionado é controlado pela interface.
  const EQUIPMENT_ROUTES = {
    ac: { on: ep.acOn, off: ep.acCut }
  };

  /* Valida o texto do display OLED ANTES de enviar (mesma regra do fluxo: não vazio e até config.OLED_MAX caracteres).
     Devolve null se estiver OK, ou a mensagem de erro para o usuário. */
  function validateOledMessage(text) {
    const t = String(text === undefined || text === null ? '' : text).trim();
    if (!t) return 'Digite uma mensagem antes de enviar.';
    // .length (unidades UTF-16) é a mesma contagem usada pelo fluxo do Node-RED e pelo maxlength do campo de texto.
    if (t.length > cfg.OLED_MAX) return `A mensagem tem ${t.length} caracteres; o limite do display é ${cfg.OLED_MAX}.`;
    return null;
  }

  CS.services.api = {
    getRoomProfile() { return CS.data.roomProfile; },                     // [BACKEND] futuro: GET sala + equipamentos

    /* GET /api/v1/telemetria. A resposta bruta fica em CampusSmart.lastRawTelemetry (útil para conferir os nomes dos campos no DevTools). */
    async getTelemetria() {
      const raw = await http.request(ep.telemetria);
      CS.lastRawTelemetry = raw;
      return normalizeTelemetry(raw);
    },

    // Liga/desliga um equipamento da Sala 101. Só resolve quando a API responde 2xx (nunca simula sucesso).
    setEquipment(equipId, turnOn) {
      const route = EQUIPMENT_ROUTES[equipId];
      if (!route) return Promise.reject(new http.ApiError('http', 404));
      return http.request((turnOn ? route.on : route.off)(cfg.ROOM_ID), { method: 'POST', body: { room_id: cfg.ROOM_ID } });
    },
    // POST /api/v1/comando-carga  { comando: 'ON' | 'OFF' | 'AUTO' }  (qualquer outro valor é recusado antes de sair do navegador)
    sendLoadCommand(cmd) {
      if (!['ON', 'OFF', 'AUTO'].includes(cmd)) return Promise.reject(new http.ApiError('http', 400));
      return http.request(ep.comandoCarga, { method: 'POST', body: { comando: cmd } });
    },
    /* POST /api/v1/mensagem  campo "mensagem" (limite em config.OLED_MAX). Texto inválido é recusado aqui, sem sair do navegador.
       Resolve com a resposta do Node-RED (ex.: { ok:true, exibindo:"..." }). O 2xx confirma que o Node-RED RECEBEU a mensagem;
       se ela chegou ao display físico depende do fluxo/dispositivo, que não informa isso nesta versão da API. */
    sendOledMessage(text) {
      const problem = validateOledMessage(text);
      if (problem) return Promise.reject(new http.ApiError('validation', 0, problem));
      return http.request(ep.mensagem, { method: 'POST', body: { mensagem: String(text).trim() } });
    },

    validateOledMessage,
    normalizeTelemetry
  };
})();
