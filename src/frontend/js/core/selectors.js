/* Visões derivadas do estado (sem DOM): equipamentos, alertas e contadores da Sala 101. */
(function () {
  const CS = window.CampusSmart; const A = CS.core.alerts;

  /* status: on (ligado) | off (desligado) | cut (chave ligada, mas a carga está cortada: sem energia) |
   unknown (a API não informa) | problem (sem comunicação). */
  function equipment(st) {
    const t = st.telemetry, room = st.room; if (!room) return [];
    return room.equipment.map(eq => {
      const v = t ? t[eq.telemetryKey] : undefined, supported = typeof v === 'boolean';
      const cut = supported && v === true && t.cargaLigada === false;       // ligado no equipamento, mas sem alimentação
      let status = !supported ? 'unknown' : cut ? 'cut' : v ? 'on' : 'off';
      if (st.online === false) status = 'problem';
      const waste = supported && v === true && !cut && t.ocupada === false;  // só há desperdício se a carga está energizada
      return Object.assign({}, eq, { on: supported ? v : undefined, supported, cut, status, waste });
    });
  }
  const alerts = st => A.annotate(A.deriveAlerts(st.room || { equipment: [] }, st.telemetry));
  function counts(st) {
    const eq = equipment(st), al = alerts(st), known = eq.filter(e => e.supported);
    return { on: known.filter(e => e.on && !e.cut).length, known: known.length, total: eq.length, alerts: al.length,
      high: al.filter(a => a.level === 'high').length, medium: al.filter(a => a.level === 'medium').length, low: al.filter(a => a.level === 'low').length };
  }
  CS.core.selectors = { equipment, alerts, counts };
})();
