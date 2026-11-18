/* Emulador mínimo do runtime HTTP do Node-RED, só para TESTES.
   Executa o JSON REAL do fluxo (nós http in / function / http response / catch / inject).
   Reproduz o comportamento relevante ao CORS:
   - http in só registra get/post/put/delete/patch (method "options" NÃO é registrado);
   - sem handler OPTIONS, o Express responde 200 + Allow, SEM cabeçalhos CORS;
   - com NR_HTTPNODECORS=1 imita `httpNodeCors` do settings.js (OPTIONS * -> 204 + cabeçalhos).
   Uso: node nodered-emulator.js <fluxo.json> [porta]   */
const http = require('http'), vm = require('vm'), fs = require('fs');
const flow = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const PORT = Number(process.argv[3] || 1880);
const USE_NODE_CORS = process.env.NR_HTTPNODECORS === '1';
const NODE_CORS_ORIGINS = ['http://127.0.0.1:5500', 'http://localhost:5500'];
const byId = Object.fromEntries(flow.map(n => [n.id, n]));
const tab = flow.find(n => n.type === 'tab');
const envVars = Object.fromEntries(((tab && tab.env) || []).map(e => [e.name, e.value]));
const globalCtx = {}; const stats = { duplicateResponses: 0, errors: [], warns: [], requests: [] };
const ctx = { get: k => globalCtx[k], set: (k, v) => { globalCtx[k] = v; } };
const compiled = {};
function fn(node) {
  return compiled[node.id] || (compiled[node.id] = new vm.Script('(function(msg,global,env,node,flow,context){' + node.func + '\n})').runInThisContext());
}
const routes = flow.filter(n => n.type === 'http in' && ['get', 'post', 'put', 'delete', 'patch'].includes(String(n.method).toLowerCase()))
  .map(n => { const keys = []; const re = new RegExp('^' + n.url.replace(/:([A-Za-z_]+)/g, (_, k) => { keys.push(k); return '([^/]+)'; }) + '/?$'); return { n, re, keys, method: n.method.toLowerCase() }; });
const anyPathMatch = p => routes.some(r => r.re.test(p));

function run(node, msg, res) {
  if (!node) return;
  if (node.type === 'http in') {
    (node.wires[0] || []).forEach(w => run(byId[w], Object.assign({}, msg), res));
  } else if (node.type === 'function') {
    let out;
    try {
      out = fn(node)(msg, ctx, { get: k => envVars[k] }, { status() {}, warn: t => stats.warns.push(String(t)), error: t => stats.errors.push(String(t)) }, ctx, ctx);
    } catch (e) {
      stats.errors.push(node.id + ': ' + e.message);
      flow.filter(c => c.type === 'catch' && (!c.scope || c.scope.length === 0 || c.scope.includes(node.id)))
        .forEach(c => (c.wires[0] || []).forEach(w => run(byId[w], Object.assign({}, msg, { error: { message: e.message } }), res)));
      return;
    }
    if (out === null || out === undefined) return;
    (node.wires[0] || []).forEach(w => run(byId[w], Object.assign({}, out), res));
  } else if (node.type === 'http response') {
    if (res.headersSent) { stats.duplicateResponses++; return; }
    const h = Object.assign({}, res._pre, msg.headers || {});
    let body = msg.payload, status = msg.statusCode || 200;
    if (body !== null && typeof body === 'object' && !Buffer.isBuffer(body)) { h['Content-Type'] = h['Content-Type'] || 'application/json'; body = JSON.stringify(body); }
    res.writeHead(status, h); res.end(body === undefined ? '' : body);
  }
}
const server = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x'); const path = url.pathname; const origin = req.headers.origin || '';
  if (path.startsWith('/__emu/')) {                       // administração dos testes
    res.setHeader('Content-Type', 'application/json');
    if (path === '/__emu/stats') return res.end(JSON.stringify(Object.assign({ state: globalCtx.campus }, stats)));
    if (path === '/__emu/reset') { delete globalCtx.campus; stats.duplicateResponses = 0; stats.errors = []; stats.warns = []; stats.requests = []; return res.end('{}'); }
    const sm = path.match(/^\/__emu\/set\/(\w+)\/(.+)$/);          // altera um campo do estado global (ex.: envelhecer o timestamp)
    if (sm && globalCtx.campus) { globalCtx.campus[sm[1]] = JSON.parse(decodeURIComponent(sm[2])); return res.end(JSON.stringify({ state: globalCtx.campus })); }
    const m = path.match(/^\/__emu\/inject\/(.+)$/);
    if (m && byId[m[1]]) { (byId[m[1]].wires[0] || []).forEach(w => run(byId[w], {}, {})); return res.end(JSON.stringify({ state: globalCtx.campus })); }
    res.statusCode = 404; return res.end('{}');
  }
  const chunks = []; req.on('data', c => chunks.push(c));
  req.on('end', () => {
    const raw = Buffer.concat(chunks); const ct = req.headers['content-type'] || '';
    stats.requests.push({ method: req.method, path, origin, contentType: ct });
    res._pre = {};
    if (USE_NODE_CORS) {                                  // cors(httpNodeCors) registrado como OPTIONS * e em cada rota
      const ok = NODE_CORS_ORIGINS.includes(origin);
      if (ok) { res._pre['Access-Control-Allow-Origin'] = origin; res._pre['Vary'] = 'Origin'; }
      if (req.method === 'OPTIONS') {
        if (ok) { res.writeHead(204, Object.assign({}, res._pre, { 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS', 'Access-Control-Allow-Headers': 'Content-Type, Accept', 'Access-Control-Max-Age': '600', 'Content-Length': '0' })); } else res.writeHead(204);
        return res.end();
      }
    }
    const r = routes.find(r => r.method === req.method.toLowerCase() && r.re.test(path));
    if (!r) {
      if (req.method === 'OPTIONS' && anyPathMatch(path)) { res.writeHead(200, { Allow: 'GET,HEAD,POST', 'Content-Type': 'text/html' }); return res.end('GET,HEAD,POST'); } // Express automático, sem CORS
      res.writeHead(404, { 'Content-Type': 'text/plain' }); return res.end('Cannot ' + req.method + ' ' + path);
    }
    const mm = path.match(r.re); const params = {}; r.keys.forEach((k, i) => params[k] = mm[i + 1]);
    let payload;
    if (req.method === 'GET') payload = Object.fromEntries(url.searchParams);
    else if (/application\/json/.test(ct)) { try { payload = JSON.parse(raw.toString()); } catch { payload = undefined; } }
    else if (/application\/x-www-form-urlencoded/.test(ct)) payload = Object.fromEntries(new URLSearchParams(raw.toString('utf8')));  // urlencoded -> objeto (como o Node-RED)
    else if (!ct || /^text\//.test(ct)) payload = raw.toString('utf8');   // text/* (ou sem tipo) -> string, como o rawBodyParser do Node-RED
    else payload = raw.length ? raw : '';                 // outros tipos -> Buffer
    const msg = { req: { params, headers: req.headers, body: payload, method: req.method, url: req.url }, payload };
    run(r.n, msg, res);
  });
});
server.listen(PORT, 'localhost', () => console.log('emulador Node-RED em http://localhost:' + PORT));
