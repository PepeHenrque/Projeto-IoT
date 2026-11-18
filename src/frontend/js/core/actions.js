/* AÇÕES DO USUÁRIO (comandos). Orquestram: confirmação + serviço (CS.services.api) + histórico + atualização da telemetria.
   O sucesso só é exibido depois que o Node-RED responde 2xx (runCommand aguarda a requisição). */
(function () {
  const CS = window.CampusSmart; const store = CS.core.store, modal = CS.ui.modal, api = CS.services.api, sel = CS.core.selectors, hist = CS.services.history;

  const refresh = () => CS.core.telemetry.fetchOnce();

  /* Envolve a requisição para registrar o resultado (sucesso/erro) no histórico de comandos. */
  const track = (label, fn, detailOk) => async () => {
    try { const r = await fn(); hist.recordCommand({ label, status: 'sucesso', detail: detailOk }); return r; }
    catch (err) { hist.recordCommand({ label, status: 'erro', detail: modal.errorContent(err).title }); throw err; }
  };

  function requestToggle(equipId, turnOn) {
    const eq = sel.equipment(store.get()).find(e => e.id === equipId), room = store.get().room;
    if (!eq || !eq.supported || store.get().busy) return;
    const verb = turnOn ? 'ligar' : 'desligar', label = `${turnOn ? 'Ligar' : 'Desligar'} ${eq.name.toLowerCase()}`;
    modal.show({
      type: 'confirm', title: `Tem certeza que deseja ${verb} este equipamento?`, text: `${eq.name} · ${room.name}`,
      actions: [{ label: 'Cancelar' }, { label: turnOn ? 'Ligar' : 'Desligar', cls: turnOn ? 'primary' : 'danger', onClick: () => modal.runCommand({
        loadingText: `${turnOn ? 'Ligando' : 'Desligando'} ${eq.name} (${room.name})…`,
        request: track(label, () => api.setEquipment(eq.id, turnOn)),
        successTitle: turnOn ? 'Equipamento ligado' : 'Equipamento desligado',
        successText: `${eq.name} (${room.name}) foi ${turnOn ? 'ligado' : 'desligado'} com sucesso.`,
        onSuccess: refresh
      }) }]
    });
  }

  function sendLoad(cmd) {
    const labels = { ON: 'Modo ON: carga ligada.', OFF: 'Modo OFF: carga desligada.', AUTO: 'Modo AUTO: a carga segue a lógica automática.' };
    modal.runCommand({
      loadingText: `Enviando comando ${cmd}…`, request: track(`Modo da carga: ${cmd}`, () => api.sendLoadCommand(cmd)),
      successTitle: 'Comando enviado', successText: labels[cmd], onSuccess: refresh
    });
  }

  /* Mensagem ao display OLED. Valida antes (vazia / acima de config.OLED_MAX) e só mostra sucesso após 2xx do Node-RED.
     O texto de sucesso diz o que de fato foi confirmado: o Node-RED RECEBEU a mensagem. A API atual não informa se o
     display físico a exibiu; no modo ?mock= a resposta é marcada explicitamente como SIMULAÇÃO. */
  function sendOled(text, onDone) {
    const msg = String(text || '').trim();
    const problem = api.validateOledMessage(msg);
    if (problem) { modal.show({ type: 'error', title: 'Mensagem inválida', text: problem, actions: [{ label: 'Fechar', cls: 'primary' }] }); return; }
    modal.runCommand({
      loadingText: 'Enviando mensagem ao display…', request: track('Mensagem ao display OLED', () => api.sendOledMessage(msg), `“${msg}”`),
      successTitle: 'Mensagem enviada',
      successText: res => (res && res.simulado)
        ? 'SIMULAÇÃO: nenhum servidor ou display real recebeu esta mensagem (modo de teste ?mock).'
        : `O servidor confirmou o recebimento${res && typeof res.exibindo === 'string' ? `: “${res.exibindo}”` : ''}. Ela foi enviada ao ESP32 via MQTT e aparece no display em alguns segundos.`,
      autoClose: 0, onSuccess: onDone
    });
  }

  CS.core.actions = { requestToggle, sendLoad, sendOled };
})();
