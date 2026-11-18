/* DASHBOARD: identificação da Sala 101, ocupação, POTÊNCIA ATUAL (W/kW) e CONSUMO ACUMULADO (kWh) como indicadores
   separados, gráfico de potência, temperatura, umidade, estado da carga e do ar-condicionado, alertas de desperdício.
   Todos os valores vêm da telemetria (GET /api/v1/telemetria); se um campo não vier, mostra "Não informado" — nunca um número fixo.
   Estrutura montada uma vez; depois só o que mudou é atualizado. */
(function () {
  const CS = window.CampusSmart; const sel = CS.core.selectors; const { esc, setHtml, emptyBox } = CS.ui.html; const S = CS.views.shared;
  const $ = (s, r) => r.querySelector(s);
  const fmt = S.fmt;

  const SKELETON = `
    <div class="room-head"><div><h1 id="dbName"></h1><p class="muted" id="dbSub">Monitoramento de energia</p></div><span class="status-badge" id="dbOcc">—</span></div>
    <div class="section-heading"><h2>Consumo de energia</h2><small class="muted-inline" id="lastUpdate">—</small></div>
    <div class="energy-grid">
      <article class="energy-card" id="cardPower" aria-live="off">
        <span class="metric-label">Potência atual</span>
        <b><span id="mPower">—</span><em id="mPowerUnit">W</em></b>
        <small id="mPowerNote">Valor instantâneo</small>
      </article>
      <article class="energy-card" id="cardEnergy" aria-live="off">
        <span class="metric-label">Consumo acumulado</span>
        <b><span id="mEnergy">—</span><em>kWh</em></b>
        <small id="mEnergyNote">Energia acumulada</small>
      </article>
    </div>
    <p class="summary-line load-line" id="dbLoad" hidden></p>
    <div class="spark-card" aria-hidden="true" hidden><svg id="spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline points=""/></svg><small>Potência — últimas leituras</small></div>
    <div class="section-heading"><h2>Ambiente</h2></div>
    <div class="metrics" id="metrics">
      <article class="metric"><span class="metric-label">Temperatura</span><b><span id="mTemp">—</span><em>°C</em></b></article>
      <article class="metric"><span class="metric-label">Umidade</span><b><span id="mHum">—</span><em>%</em></b></article>
    </div>
    <div class="section-heading"><h2>Equipamento</h2><a class="link" href="#/controle">Controlar</a></div>
    <div id="dbEquip"></div>
    <div class="section-heading"><h2>Alertas de desperdício</h2><a class="link" href="#/alertas">Ver todos</a></div>
    <div id="dbAlerts"></div>`;

  function equipRows(st) {
    const eq = sel.equipment(st);
    return `<div class="equipment-list">${eq.map(e => `<div class="equipment" data-equip-row="${esc(e.id)}">
      <span class="equip-icon" aria-hidden="true">${e.icon}</span>
      <span class="device-info"><b>${esc(e.name)}</b>${e.waste ? '<small class="warning">Ligado sem necessidade: sala vazia</small>' : e.cut ? '<small>Carga cortada: sem energia</small>' : ''}</span>${S.stateBadge(e)}</div>`).join('')}</div>`;
  }
  function alertRows(st) {
    const al = sel.alerts(st);
    if (!al.length) return emptyBox('Nenhum desperdício identificado', 'Não há equipamentos ligados sem necessidade na Sala 101.');
    return `<div class="recent-item">${al.slice(0, 3).map(a => `<a class="recent-row" href="#/alertas"><span class="dot ${a.level === 'medium' ? 'medium' : a.level === 'low' ? 'low' : ''}"></span><span class="recent-copy"><b>${esc(a.equip)}</b><small>${esc(a.reason)}</small></span>${CS.ui.html.priorityTag(a.level, a.priority)}</a>`).join('')}</div>`;
  }

  /* Potência atual e consumo acumulado: dois indicadores independentes (potência ≠ energia). */
  function paintEnergy(r, t, stale) {
    const p = S.formatPower(t.potencia), e = S.formatEnergy(t.energia);
    $('#mPower', r).textContent = p.value; $('#mPowerUnit', r).textContent = p.unit;
    $('#mEnergy', r).textContent = e.value;
    $('#mPowerNote', r).textContent = t.potencia === null ? 'Não informado pela telemetria' : p.detail ? `Instantâneo · ${p.detail}` : 'Valor instantâneo';
    $('#mEnergyNote', r).textContent = t.energia === null ? 'Não informado pela telemetria' : 'Energia acumulada';
    $('#cardPower', r).classList.toggle('missing', t.potencia === null); $('#cardEnergy', r).classList.toggle('missing', t.energia === null);
    $('#cardPower', r).classList.toggle('stale', stale); $('#cardEnergy', r).classList.toggle('stale', stale);
    const load = $('#dbLoad', r);                                      // estado efetivo da carga (modo ON/OFF/AUTO)
    load.hidden = !t.modoCarga;
    if (t.modoCarga) load.textContent = `Carga: ${t.cargaLigada === undefined ? 'estado não informado' : t.cargaLigada ? 'energizada' : 'cortada'} · modo ${t.modoCarga}`;
  }

  const view = {
    root: null, built: false,
    mount(root) { this.root = root; this.built = false; this.update(); },
    update() {
      const st = CS.core.store.get(), gate = S.telemetryGate(st);
      if (gate) { this.built = false; setHtml(this.root, `<h1>Início</h1><p class="muted">Sala 101</p>${gate}`); return; }
      if (!this.built) { this.root.innerHTML = SKELETON; this.root._last = null; this.built = true; $('#dbName', this.root).textContent = st.room.name; }
      const r = this.root, t = st.telemetry;
      const occ = $('#dbOcc', r); occ.textContent = t.ocupada === undefined ? 'Ocupação não informada' : t.ocupada ? 'Ocupada' : 'Vazia'; occ.classList.toggle('occupied', t.ocupada === true);
      $('#mTemp', r).textContent = fmt(t.temperatura, 1); $('#mHum', r).textContent = fmt(t.umidade, 0);
      paintEnergy(r, t, st.online === false);
      $('#lastUpdate', r).textContent = (st.online ? 'Atualizado ' : 'Desatualizado · ') + S.hhmmss(t.ts);
      $('#metrics', r).classList.toggle('stale', st.online === false);
      $('#dbSub', r).textContent = st.online ? 'Monitoramento de energia em tempo real' : 'Sem comunicação com o ESP32 ou o servidor';
      const h = st.history, card = $('.spark-card', r); card.hidden = h.length < 2;
      if (h.length >= 2) {
        const min = Math.min(...h), max = Math.max(...h), span = max - min || 1;
        $('#spark polyline', r).setAttribute('points', h.map((v, i) => `${(i / (h.length - 1) * 100).toFixed(1)},${(28 - ((v - min) / span) * 26).toFixed(1)}`).join(' '));
      }
      setHtml($('#dbEquip', r), equipRows(st)); setHtml($('#dbAlerts', r), alertRows(st));
    }
  };
  CS.views.dashboard = view;
})();
