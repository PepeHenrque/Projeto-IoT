/* CONTROLE DA SALA 101: liga/desliga o ar-condicionado, modo da carga (ON/OFF/AUTO) e mensagem ao display OLED.
   O estado mostrado vem da telemetria (nunca do clique). O controle só fica ativo quando o Node-RED informa o estado. */
(function () {
  const CS = window.CampusSmart; const sel = CS.core.selectors; const { esc, setHtml } = CS.ui.html; const S = CS.views.shared;
  const $ = (s, r) => r.querySelector(s);

  const STATIC = `
    <h1>Controle da sala</h1><p class="muted" id="ctSub">Sala 101 · comandos enviados ao ESP32</p>
    <div class="section-heading"><h2>Equipamento</h2></div>
    <div id="ctEquip"></div>
    <div class="section-heading"><h2>Modo da carga</h2></div>
    <div class="card">
      <p class="card-hint">Modo atual: <b id="loadMode">—</b> · Carga: <b id="loadState">—</b></p>
      <p class="card-hint">ON liga a carga · OFF corta a carga · AUTO deixa a lógica automática decidir.</p>
      <div class="segmented" id="loadControl" role="group" aria-label="Modo da carga">
        <button type="button" data-action="load" data-cmd="ON" aria-pressed="false">ON</button>
        <button type="button" data-action="load" data-cmd="OFF" aria-pressed="false">OFF</button>
        <button type="button" data-action="load" data-cmd="AUTO" aria-pressed="false">AUTO</button>
      </div>
    </div>
    <div class="section-heading"><h2>Mensagem no display OLED</h2></div>
    <div class="card">
      <label class="sr-only" for="oledText">Mensagem para o display</label>
      <p class="card-hint">Texto enviado ao servidor, que repassa via MQTT ao display da sala (até ${CS.config.OLED_MAX} caracteres).</p>
      <textarea id="oledText" rows="2" maxlength="${CS.config.OLED_MAX}" placeholder="Digite a mensagem (ex.: Desligue o ar ao sair)"></textarea>
      <div class="oled-foot"><small class="muted-inline" id="oledCounter"><span id="oledCount">0</span>/${CS.config.OLED_MAX}</small>
        <button class="btn primary" id="oledSend" type="button" data-action="oled-send" disabled>Enviar ao display</button></div>
    </div>`;

  function equipCard(e, busy) {
    const dis = busy ? 'disabled' : '';
    let action;
    if (!e.supported) action = '<p class="muted">O dispositivo não informou o estado deste equipamento: controle indisponível.</p>';
    else if (e.on) action = `<button class="btn danger-outline block" type="button" data-action="toggle" data-equip="${esc(e.id)}" data-turn="off" ${dis}>${esc(e.turnOffLabel)}</button>`;
    else action = `<button class="btn primary block" type="button" data-action="toggle" data-equip="${esc(e.id)}" data-turn="on" ${dis}>${esc(e.turnOnLabel)}</button>`;
    return `<div class="equip-card ${esc(e.status)}" data-equip-card="${esc(e.id)}">
      <div class="equip-top"><span class="equip-icon" aria-hidden="true">${e.icon}</span><span class="device-info"><b>${esc(e.name)}</b>
        <small>${e.status === 'problem' && e.supported ? `Último estado conhecido: ${esc(e.on ? e.onText : e.offText)}` : 'Estado atual'}</small></span>${S.stateBadge(e)}</div>
      ${e.waste ? '<p class="waste-line">⚠️ Ligado sem necessidade: a sala está vazia</p>' : ''}${e.cut ? '<p class="cut-line">⏻ A carga está cortada: o equipamento está sem energia</p>' : ''}${action}</div>`;
  }

  const view = {
    root: null, built: false,
    mount(root) { this.root = root; this.built = false; this.update(); },
    update() {
      const st = CS.core.store.get(), gate = S.telemetryGate(st), r = this.root;
      if (gate) { this.built = false; setHtml(r, `<h1>Controle da sala</h1><p class="muted">Sala 101</p>${gate}`); return; }
      if (!this.built) {
        r.innerHTML = STATIC; r._last = null; this.built = true;
        const ta = $('#oledText', r); ta.maxLength = CS.config.OLED_MAX;
        ta.addEventListener('input', () => { $('#oledCount', r).textContent = ta.value.length; this.paintForm(); });
      }
      setHtml($('#ctEquip', r), sel.equipment(st).map(e => equipCard(e, st.busy)).join(''));
      this.paintForm();
    },
    paintForm() {                       // parte que não pode ser recriada (campo de texto em edição)
      const r = this.root, st = CS.core.store.get(), t = st.telemetry; if (!t || !$('#loadControl', r)) return;
      $('#loadMode', r).textContent = t.modoCarga || '—';
      $('#loadState', r).textContent = t.cargaLigada === undefined ? 'não informado' : t.cargaLigada ? 'energizada' : 'cortada';   // estado EFETIVO, vindo da telemetria
      r.querySelectorAll('#loadControl button').forEach(b => { b.setAttribute('aria-pressed', String(t.modoCarga === b.dataset.cmd)); b.disabled = st.busy; });
      $('#oledSend', r).disabled = st.busy || !$('#oledText', r).value.trim();
    }
  };
  CS.views.control = view;
})();
