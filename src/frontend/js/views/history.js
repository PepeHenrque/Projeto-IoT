/* HISTÓRICO: consumo, alterações de estado e comandos enviados (com horário).
   Mostra só o que existe (registros da sessão) e deixa claro que o histórico persistente virá do back-end/banco. */
(function () {
  const CS = window.CampusSmart; const { esc, setHtml, loadingBox } = CS.ui.html; const S = CS.views.shared;
  const fmt = (v, d) => v === null || v === undefined ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d });
  const empty = t => `<div class="equipment"><span class="device-info"><small>${esc(t)}</small></span></div>`;

  function render() {
    const h = CS.services.history.get();
    if (!h.ready) return `<h1>Histórico</h1><p class="muted">Sala 101</p>${loadingBox('Carregando histórico…')}`;
    const note = h.source === 'session'
      ? '<div class="note" id="histNote"><b>Registros desta sessão.</b> Ficam apenas na memória do navegador e somem ao recarregar a página. O histórico completo será fornecido pelo back-end e pelo banco de dados (etapa futura).</div>' : '';
    const c = h.consumption, last = c.slice(-10).reverse();
    const vals = c.map(x => x.potencia), avg = vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : null;
    return `<h1>Histórico</h1><p class="muted">Sala 101</p>${note}
      <div class="section-heading"><h2>Consumo de energia</h2></div>
      ${c.length ? `<div class="priority-stats"><article><b>${c.length}</b><span>Leituras</span></article><article><b>${fmt(avg, 0)}</b><span>Média (W)</span></article><article><b>${fmt(Math.max(...vals), 0)}</b><span>Máxima (W)</span></article></div>` : ''}
      <div class="equipment-list" id="histConsumption">${last.length ? `<div class="hist-row head"><span>Hora</span><span>Potência</span><span>Energia</span></div>${last.map(x => `<div class="hist-row"><span>${esc(S.hhmmss(x.ts))}</span><span>${fmt(x.potencia, 0)} W</span><span>${fmt(x.energia, 2)} kWh</span></div>`).join('')}` : empty('Ainda não há leituras de consumo.')}</div>
      <div class="section-heading"><h2>Alterações de estado</h2></div>
      <div class="equipment-list" id="histStates">${h.states.length ? h.states.slice().reverse().map(x => `<div class="hist-row two"><span>${esc(S.hhmmss(x.ts))}</span><span><b>${esc(x.equip)}</b>: ${esc(x.from)} → ${esc(x.to)}</span></div>`).join('') : empty('Nenhuma alteração de estado registrada.')}</div>
      <div class="section-heading"><h2>Comandos enviados</h2></div>
      <div class="equipment-list" id="histCommands">${h.commands.length ? h.commands.slice().reverse().map(x => `<div class="hist-row two"><span>${esc(S.hhmmss(x.ts))}</span><span><b>${esc(x.label)}</b> · <span class="${x.status === 'sucesso' ? 'ok-text' : 'err-text'}">${x.status === 'sucesso' ? 'Sucesso' : 'Erro'}</span>${x.detail ? ` <small>${esc(x.detail)}</small>` : ''}</span></div>`).join('') : empty('Nenhum comando enviado nesta sessão.')}</div>`;
  }
  CS.views.history = {
    mount(root) { this.root = root; this.update(); },
    update() { setHtml(this.root, render()); }
  };
})();
