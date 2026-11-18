/* Polling da telemetria (GET /api/v1/telemetria). Pausa quando a aba está oculta. */
(function () {
  const CS = window.CampusSmart; const store = CS.core.store; let inflight = false, again = false, timer = null;

  async function fetchOnce() {
    if (inflight) { again = true; return; } inflight = true;
    try {
      const t = await CS.services.api.getTelemetria();
      CS.services.history.recordTelemetry(t);
      let history = store.get().history;
      if (t.potencia !== null) history = history.concat(t.potencia).slice(-CS.config.SPARK_POINTS);
      store.set({ telemetry: t, online: true, connKind: null, history });
    } catch (err) {
      store.set({ online: false, connKind: err.kind || 'network' });
    } finally { inflight = false; if (again) { again = false; fetchOnce(); } }
  }
  function start() {
    fetchOnce(); clearInterval(timer); timer = setInterval(fetchOnce, CS.config.POLL_MS);
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) { clearInterval(timer); timer = null; } else { fetchOnce(); timer = setInterval(fetchOnce, CS.config.POLL_MS); }
    });
  }
  CS.core.telemetry = { start, fetchOnce };
})();
