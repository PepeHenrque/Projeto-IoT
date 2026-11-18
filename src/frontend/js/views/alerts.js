/* ALERTAS: equipamento, motivo, tipo de desperdício, prioridade e estado. Mensagem quando não há desperdícios. */
(function () {
  const CS = window.CampusSmart; const sel = CS.core.selectors; const { setHtml, emptyBox } = CS.ui.html; const S = CS.views.shared;
  function render(st) {
    const gate = S.telemetryGate(st); if (gate) return `<h1>Alertas</h1><p class="muted">Desperdícios identificados</p>${gate}`;
    const c = sel.counts(st), alerts = sel.alerts(st);
    const stale = st.online === false ? `<div class="note warn" role="status">Sem comunicação com o servidor: os alertas usam a última leitura (${S.hhmmss(st.telemetry.ts)}) e podem estar desatualizados.</div>` : '';
    return `<h1>Alertas</h1><p class="muted">${c.alerts} ${c.alerts === 1 ? 'desperdício identificado' : 'desperdícios identificados'} na Sala 101</p>${stale}
      <div class="priority-stats">
        <article><b class="high">${c.high}</b><span>Alta</span></article>
        <article><b class="medium">${c.medium}</b><span>Média</span></article>
        <article><b class="low">${c.low}</b><span>Baixa</span></article>
      </div>
      ${alerts.length ? `<div class="alerts-list">${alerts.map(S.alertCard).join('')}</div>` : emptyBox('Nenhum desperdício identificado', 'Quando um equipamento ficar ligado com a sala vazia, o alerta aparecerá aqui.')}`;
  }
  CS.views.alerts = { mount(root) { this.root = root; this.update(); }, update() { setHtml(this.root, render(CS.core.store.get())); } };
})();
