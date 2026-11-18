/* Modal único de feedback: confirmação | carregando | sucesso | erro. */
(function () {
  const CS = window.CampusSmart; const store = CS.core.store;
  const $ = s => document.querySelector(s);
  let lock = false, closeTimer = null, lastFocus = null;

  function close() {
    clearTimeout(closeTimer);
    const m = $('#modal'); m.classList.remove('show'); m.setAttribute('aria-hidden', 'true'); lock = false;
    if (lastFocus && document.contains(lastFocus)) lastFocus.focus();
  }

  function show({ type, title, text, actions = [], locked = false, autoClose = 0 }) {
    const m = $('#modal'), box = m.querySelector('.modal');
    clearTimeout(closeTimer);
    if (!m.classList.contains('show')) lastFocus = document.activeElement;
    lock = locked; box.dataset.type = type;
    const sym = $('#modalSymbol'); sym.textContent = '';
    if (type === 'loading') { const s = document.createElement('div'); s.className = 'spinner'; sym.appendChild(s); }
    else sym.textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : '!';
    $('#modalTitle').textContent = title; $('#modalText').textContent = text || '';
    const bar = $('#modalActions'); bar.textContent = '';
    actions.forEach(a => {
      const b = document.createElement('button'); b.type = 'button'; b.className = 'btn ' + (a.cls || ''); b.textContent = a.label;
      b.addEventListener('click', a.onClick || close); bar.appendChild(b);
    });
    m.classList.add('show'); m.setAttribute('aria-hidden', 'false');
    const first = bar.querySelector('button:last-child'); if (first) first.focus();
    if (autoClose) closeTimer = setTimeout(close, autoClose);
  }

  function errorContent(err) {
    if (err.kind === 'offline') return { title: 'Dispositivo offline', text: 'O dispositivo não respondeu (erro 503). Verifique a energia e a rede do equipamento e tente novamente.' };
    if (err.kind === 'timeout') return { title: 'Tempo esgotado', text: 'O servidor demorou demais para responder. Tente novamente.' };
    if (err.kind === 'network') return { title: 'Sem conexão', text: 'Não foi possível falar com o servidor. Verifique sua rede e tente novamente.' };
    if (err.kind === 'validation') return { title: 'Mensagem inválida', text: err.detail || 'Revise o texto e tente novamente.', retry: false };
    // Outros códigos: mostra o motivo devolvido pela API (ex.: {"erro":"mensagem vazia ou maior que 64 caracteres"}), se houver.
    const why = err.detail ? ` Motivo informado pelo servidor: “${err.detail}”.` : '';
    return { title: 'Não foi possível executar o comando', text: `O servidor recusou a requisição (código ${err.status}).${why}` };
  }

  /* Executa um comando com os estados: carregando → sucesso (só após a API confirmar) | erro com "Tentar novamente". */
  async function runCommand(opts) {
    if (store.get().busy) return;
    store.set({ busy: true });
    show({ type: 'loading', title: 'Enviando comando…', text: opts.loadingText, locked: true });
    try {
      const res = await opts.request();
      store.set({ busy: false });
      if (opts.onSuccess) opts.onSuccess(res);
      const text = typeof opts.successText === 'function' ? opts.successText(res) : opts.successText;
      show({ type: 'success', title: opts.successTitle, text, autoClose: opts.autoClose === undefined ? 1800 : opts.autoClose, actions: [{ label: 'OK', cls: 'primary' }] });
    } catch (err) {
      store.set({ busy: false });
      const c = errorContent(err);
      // Erro de validação não se resolve repetindo o envio: só "Fechar".
      const actions = c.retry === false ? [{ label: 'Fechar', cls: 'primary' }] : [{ label: 'Fechar' }, { label: 'Tentar novamente', cls: 'primary', onClick: () => runCommand(opts) }];
      show({ type: 'error', title: c.title, text: c.text, actions });
    }
  }

  $('#modal').addEventListener('click', e => { if (e.target.id === 'modal' && !lock) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && $('#modal').classList.contains('show') && !lock) close(); });

  CS.ui.modal = { show, close, runCommand, errorContent };
})();
