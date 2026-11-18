/* Estado único da aplicação + assinatura de mudanças. Sem DOM. */
(function () {
  const CS = window.CampusSmart;
  const state = {
    room: null,                                              // perfil da Sala 101 (equipamentos)
    telemetry: null, online: null, connKind: null, history: [], // online: null = conectando
    busy: false                                              // comando em andamento
  };
  const subs = new Set();
  CS.core.store = {
    get: () => state,
    set(patch) { Object.assign(state, patch); subs.forEach(fn => fn(state)); },
    subscribe(fn) { subs.add(fn); return () => subs.delete(fn); }
  };
})();
