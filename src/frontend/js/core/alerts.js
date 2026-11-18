/* Regras de alerta de desperdício da Sala 101 (função pura, sem DOM).
   Hoje os alertas são DERIVADOS da telemetria; no futuro podem vir prontos do back-end (GET alertas). */
(function () {
  const CS = window.CampusSmart;
  const LABEL = { high: 'Alta', medium: 'Média', low: 'Baixa' };
  const ORDER = { high: 0, medium: 1, low: 2 };
  const firstSeen = new Map();        // estado do alerta: "Ativo desde ..." (guardado só em memória)

  /* room = perfil da sala; t = telemetria normalizada (ou null). Sem telemetria não há como afirmar nada: devolve []. */
  function deriveAlerts(room, t) {
    if (!t) return [];
    const out = [];
    if (t.ocupada === false) {        // sala vazia + equipamento ligado e ENERGIZADO = desperdício (carga cortada não consome)
      room.equipment.forEach(eq => {
        if (t[eq.telemetryKey] === true && t.cargaLigada !== false) out.push({ id: `${eq.id}-vazia`, equipId: eq.id, equip: eq.name, reason: eq.wasteReason, type: eq.wasteType, level: eq.wasteLevel });
      });
    }
    const limit = CS.config.ALERTS.HIGH_POWER_W;
    if (t.potencia !== null && t.potencia > limit) {
      out.push({ id: 'consumo-alto', equipId: null, equip: 'Consumo geral', reason: `Potência de ${Math.round(t.potencia)} W acima do limite de ${limit} W`, type: 'Consumo acima do padrão', level: 'low' });
    }
    return out.map(a => Object.assign(a, { priority: LABEL[a.level] })).sort((a, b) => ORDER[a.level] - ORDER[b.level]);
  }

  /* Acrescenta state:'ativo' e since (primeira vez em que o alerta foi visto nesta sessão). Alertas que sumiram são esquecidos. */
  function annotate(alerts) {
    const ids = new Set(alerts.map(a => a.id));
    [...firstSeen.keys()].forEach(k => { if (!ids.has(k)) firstSeen.delete(k); });
    return alerts.map(a => { if (!firstSeen.has(a.id)) firstSeen.set(a.id, new Date()); return Object.assign({}, a, { state: 'Ativo', since: firstSeen.get(a.id) }); });
  }

  CS.core.alerts = { deriveAlerts, annotate, LABEL };
})();
