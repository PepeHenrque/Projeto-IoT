/* HISTÓRICO: consumo, mudanças de estado e comandos enviados.
   Registra SÓ o que o próprio front-end observou/enviou nesta sessão, em memória. Nada é inventado e nada persiste ao recarregar.

   [BACKEND] PONTO DE INTEGRAÇÃO nº 5: o histórico persistente (consumo, estados, comandos, alertas) será fornecido pelo
   back-end/banco numa etapa futura. Nenhum endpoint de histórico existe hoje; quando existir, `get()` passará a ler dele
   e `recordTelemetry`/`recordCommand` deixarão de ser necessários. As telas só dependem do formato devolvido por `get()`. */
(function () {
  const CS = window.CampusSmart, cfg = CS.config;
  const data = { consumption: [], states: [], commands: [] };
  let last = null;
  const cap = a => { if (a.length > cfg.HISTORY_MAX) a.splice(0, a.length - cfg.HISTORY_MAX); };

  const WATCH = [   // o que é comparado entre duas leituras consecutivas para detectar "alteração de estado"
    ['Ocupação', 'ocupada', v => v ? 'Ocupada' : 'Vazia'],
    ['Ar-condicionado', 'acLigado', v => v ? 'Ligado' : 'Desligado'],
    ['Modo da carga', 'modoCarga', v => v]
  ];

  function recordTelemetry(t) {
    if (!t) return;
    if (last && last.ts && t.ts && +last.ts === +t.ts) return;       // mesma leitura repetida
    if (t.potencia !== null) { data.consumption.push({ ts: t.ts, potencia: t.potencia, energia: t.energia }); cap(data.consumption); }
    if (last) WATCH.forEach(([equip, key, fmt]) => {
      const a = last[key], b = t[key];
      if (a !== undefined && a !== null && b !== undefined && b !== null && a !== b) { data.states.push({ ts: t.ts, equip, from: fmt(a), to: fmt(b) }); cap(data.states); }
    });
    last = t;
  }
  function recordCommand({ label, status, detail }) {
    data.commands.push({ ts: new Date(), label, status, detail: detail || '' }); cap(data.commands);
  }
  const get = () => ({ source: 'session', ready: true, consumption: data.consumption.slice(), states: data.states.slice(), commands: data.commands.slice() });

  CS.services.history = { recordTelemetry, recordCommand, get };
})();
