/* SIMULAÇÃO — servidor falso para testar a interface SEM o Node-RED (nada é enviado a Node-RED ou ESP32 reais).
   Só é ativado com ?mock=... na URL; sem esse parâmetro este arquivo não faz nada e a interface usa a API real.
   As respostas de POST trazem "simulado": true, e a tela de sucesso do OLED avisa que foi uma simulação.
   Ativação: abra index.html?mock=1
   Variações: ?mock=503   → telemetria OK, comandos respondem 503 (dispositivo offline)
              ?mock=cmdnet → telemetria OK, comandos falham por rede
              ?mock=noac   → telemetria sem o campo ac (controle do ar-condicionado indisponível)
              ?mock=nopower → telemetria sem potência e sem energia (mostra "Não informado")
              ?mock=altnames → potência em kW e energia em Wh, em outro objeto (testa a leitura tolerante)
              ?mock=down  → todas as requisições falham (sem rede)
              ?mock=slow  → comandos demoram 3s (para ver o modal de carregamento) */
(function () {
  const mode = new URLSearchParams(location.search).get('mock');
  if (!mode) return;
  // Aviso fixo na tela: deixa claro que NADA desta sessão chega ao Node-RED ou ao display físico.
  const banner = () => {
    if (document.getElementById('mockBanner')) return;
    const d = document.createElement('div'); d.id = 'mockBanner'; d.className = 'mock-banner'; d.setAttribute('role', 'status');
    d.textContent = `SIMULAÇÃO (?mock=${mode}): dados e comandos falsos, nada é enviado ao Node-RED nem ao display.`;
    const phone = document.querySelector('.phone'); if (phone) phone.insertBefore(d, phone.children[1] || null);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', banner); else banner();
  const realFetch = window.fetch.bind(window);
  const s = { ocupada: false, ac: true, modo: 'ON', potencia: 1450, energia: 12.34, oled: '' };
  const carga = () => s.modo === 'ON' || (s.modo === 'AUTO' && s.ocupada === true);   // mesma regra do fluxo do Node-RED
  const OLED_MAX = 64;    // mesma regra do fluxo do Node-RED
  /* Lê o corpo como o Node-RED faria: formulário (x-www-form-urlencoded) ou JSON. */
  const readBody = (opts) => {
    const ct = (opts.headers && (opts.headers['Content-Type'] || opts.headers['content-type'])) || '';
    if (!opts.body) return {};
    if (/x-www-form-urlencoded/.test(ct)) return Object.fromEntries(new URLSearchParams(opts.body));
    try { return JSON.parse(opts.body); } catch { return {}; }
  };
  const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
  const wait = ms => new Promise(r => setTimeout(r, ms));

  window.fetch = async (url, opts = {}) => {
    const path = String(url).split('?')[0];
    if (!path.includes('/api/v1/')) return realFetch(url, opts);
    if (mode === 'down') throw new TypeError('Failed to fetch');
    if (mode === 'cmdnet' && (opts.method || 'GET').toUpperCase() === 'POST') throw new TypeError('Failed to fetch');
    const method = (opts.method || 'GET').toUpperCase();
    if (method === 'POST') (window.__calls = window.__calls || []).push({ method, path, body: readBody(opts), contentType: (opts.headers || {})['Content-Type'] || '' });
    await wait(mode === 'slow' && method === 'POST' ? 3000 : 250);

    if (path.endsWith('/telemetria') && method === 'GET') {
      s.potencia = 200 + (carga() ? (s.ac ? 1100 : 0) + 150 : 0) + Math.round((Math.random() - 0.5) * 80);
      s.energia += s.potencia / 720000;
      const raw = {
        sala: 101, timestamp: new Date().toISOString(), ocupada: s.ocupada,
        temperatura: 23.4 + Math.random(), umidade: 55 + Math.round(Math.random() * 4),
        potencia_w: Math.round(s.potencia), energia_kwh: +s.energia.toFixed(3),
        ...(mode === 'noac' ? {} : { ac: { ligado: s.ac } }), carga: { modo: s.modo, ligada: carga() }
      };
      if (mode === 'nopower') { delete raw.potencia_w; delete raw.energia_kwh; }             // telemetria sem potência/energia
      if (mode === 'altnames') {                                                                // nomes/unidades alternativos
        const w = raw.potencia_w, k = raw.energia_kwh; delete raw.potencia_w; delete raw.energia_kwh;
        raw.consumo = { potencia_kw: w / 1000, energia_wh: k * 1000 };
      }
      return json(raw);
    }
    if (method === 'POST') {
      if (mode === '503') return json({ erro: 'dispositivo offline' }, 503);
      const body = readBody(opts);
      if (path.endsWith('/ac/cut')) { if (!path.includes('/rooms/101/')) return json({ erro: 'sala não encontrada' }, 404); s.ac = false; s.potencia = Math.max(80, s.potencia - 1200); return json({ ok: true, simulado: true }); }
      if (path.endsWith('/ac/on')) { if (!path.includes('/rooms/101/')) return json({ erro: 'sala não encontrada' }, 404); s.ac = true; s.potencia += 1200; return json({ ok: true, simulado: true }); }
      if (path.endsWith('/comando-carga')) {
        const cmd = String(body.comando || '').toUpperCase();
        if (!['ON', 'OFF', 'AUTO'].includes(cmd)) return json({ erro: 'comando inválido (use ON, OFF ou AUTO)' }, 400);
        s.modo = cmd; return json({ ok: true, simulado: true, modo: s.modo, carga: { modo: s.modo, ligada: carga() } });
      }
      if (path.endsWith('/mensagem')) {
        const t = String(body.mensagem || '').trim();
        if (!t || t.length > OLED_MAX) return json({ erro: `mensagem vazia ou maior que ${OLED_MAX} caracteres` }, 400);
        s.oled = t; window.__oled = t; return json({ ok: true, simulado: true, exibindo: t });
      }
    }
    return json({ erro: 'não encontrado' }, 404);
  };
})();
