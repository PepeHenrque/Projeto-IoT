/* Bootstrap: roteador por hash (#/inicio, #/controle, #/alertas, #/historico), barra superior,
   navegação inferior e despacho dos cliques (data-action). Nenhuma regra de negócio aqui. */
(function () {
  const CS = window.CampusSmart; const store = CS.core.store, sel = CS.core.selectors;
  const $ = s => document.querySelector(s); const root = $('#view');
  let current = null;

  function parse(hash) {
    const p = String(hash || '').replace(/^#\/?/, '').split('/').filter(Boolean)[0];
    if (p === 'controle') return { view: 'control', nav: 'controle' };
    if (p === 'alertas') return { view: 'alerts', nav: 'alertas' };
    if (p === 'historico') return { view: 'history', nav: 'historico' };
    return { view: 'dashboard', nav: 'inicio' };           // qualquer outra rota cai no Dashboard
  }

  function navigate() {
    const r = parse(location.hash);
    current = CS.views[r.view];
    root.innerHTML = ''; root._last = null;
    current.mount(root);
    document.querySelectorAll('.nav-item').forEach(n => { const on = n.dataset.nav === r.nav; n.classList.toggle('active', on); if (on) n.setAttribute('aria-current', 'page'); else n.removeAttribute('aria-current'); });
    window.scrollTo(0, 0);
  }

  function paintChrome(st) {
    const pill = $('#connPill'), txt = $('#connText');
    if (st.online === null) { pill.dataset.state = 'connecting'; txt.textContent = 'Conectando…'; }
    else if (st.online) { pill.dataset.state = 'online'; txt.textContent = 'Online'; }
    else { pill.dataset.state = 'offline'; txt.textContent = st.connKind === 'offline' ? 'Dispositivo offline' : 'Sem conexão'; }
    const badge = $('#navAlertCount'), n = st.telemetry ? sel.counts(st).alerts : 0;
    badge.textContent = n; badge.hidden = n === 0;
  }

  document.addEventListener('click', e => {
    const el = e.target.closest('[data-action]'); if (!el || el.disabled) return;
    const a = el.dataset.action, act = CS.core.actions;
    if (a === 'toggle') act.requestToggle(el.dataset.equip, el.dataset.turn === 'on');
    else if (a === 'load') act.sendLoad(el.dataset.cmd);
    else if (a === 'retry-telemetry') CS.core.telemetry.fetchOnce();
    else if (a === 'oled-send') {
      const ta = $('#oledText');
      act.sendOled(ta.value, () => { ta.value = ''; $('#oledCount').textContent = '0'; CS.views.control.paintForm(); });
    }
  });

  window.addEventListener('hashchange', navigate);
  store.subscribe(st => { paintChrome(st); if (current) current.update(); });

  store.set({ room: CS.services.api.getRoomProfile() });
  navigate();
  CS.core.telemetry.start();
})();
