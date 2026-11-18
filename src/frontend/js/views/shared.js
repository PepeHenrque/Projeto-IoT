/* Pedaços de tela reutilizados por mais de uma view. */
(function () {
  const CS = window.CampusSmart; const { esc, priorityTag, loadingBox, errorBox } = CS.ui.html;
  const hhmm = d => (d instanceof Date ? d : new Date(d)).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  /* Formatação numérica pt-BR. null/undefined => '—' (nunca inventa valor). */
  const fmt = (v, min = 0, max = min) => v === null || v === undefined ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: min, maximumFractionDigits: max });
  /* Potência instantânea (entrada em W): abaixo de 1000 W mostra W; a partir de 1000 W mostra kW. */
  function formatPower(w) {
    if (w === null || w === undefined) return { value: '—', unit: 'W', detail: '' };
    return Math.abs(w) >= 1000 ? { value: fmt(w / 1000, 2), unit: 'kW', detail: `${fmt(w, 0)} W` } : { value: fmt(w, 0), unit: 'W', detail: '' };
  }
  /* Energia acumulada (entrada em kWh): 2 a 3 casas decimais (ex.: 2,45 ou 12,342). */
  const formatEnergy = kwh => ({ value: fmt(kwh, 2, 3), unit: 'kWh' });
  const hhmmss = d => (d instanceof Date ? d : new Date(d)).toLocaleTimeString('pt-BR');

  /* "Carregando…" (primeira leitura em andamento) ou erro com "Tentar novamente" (nenhuma leitura chegou). null = há dados. */
  function telemetryGate(st) {
    if (st.telemetry) return null;
    if (st.online === false) {
      const c = CS.ui.modal.errorContent({ kind: st.connKind || 'network', status: 0 });
      return errorBox('Sem comunicação com o servidor', c.text, '<button class="btn primary" type="button" data-action="retry-telemetry">Tentar novamente</button>');
    }
    return loadingBox('Carregando dados da Sala 101…');
  }

  const STATUS_TEXT = (eq) => eq.status === 'on' ? eq.onText : eq.status === 'off' ? eq.offText : eq.status === 'cut' ? 'Sem alimentação' : eq.status === 'problem' ? 'Sem comunicação' : 'Não informado';
  const stateBadge = eq => `<span class="state-badge ${esc(eq.status)}">${esc(STATUS_TEXT(eq))}</span>`;

  function alertCard(a) {
    return `<article class="alert-card ${a.level === 'high' ? 'high-border' : ''}">
      <div class="alert-top">${priorityTag(a.level, a.priority)}<span class="state-badge active">${esc(a.state)} desde ${esc(hhmm(a.since))}</span></div>
      <h3>${esc(a.reason)}</h3>
      <p><b>Equipamento:</b> ${esc(a.equip)}</p>
      <p><b>Tipo de desperdício:</b> ${esc(a.type)}</p>
      <p><b>Prioridade:</b> ${esc(a.priority)} · <b>Estado:</b> ${esc(a.state)}</p>
      ${a.equipId ? '<div class="alert-actions"><a class="btn primary" href="#/controle">Ir para o controle</a></div>' : ''}</article>`;
  }
  CS.views.shared = { telemetryGate, stateBadge, alertCard, hhmm, hhmmss, STATUS_TEXT, fmt, formatPower, formatEnergy };
})();
