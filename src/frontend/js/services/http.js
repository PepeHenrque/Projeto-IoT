/* Camada mais baixa de comunicação: ÚNICO lugar do projeto que chama fetch().
   Cuida de: endereço base (config.API_BASE), timeout, formato do corpo e erros tipados (ApiError: timeout | network | offline | http).

   FORMATO DO CORPO DOS POST (config.SIMPLE_REQUESTS):
   - true (padrão): application/x-www-form-urlencoded  →  ex.: mensagem=Ol%C3%A1
       • É uma requisição "simples" para o navegador: NÃO gera preflight OPTIONS (o Node-RED não tem nó OPTIONS).
       • O nó "http in" do Node-RED converte esse formato em OBJETO: msg.payload = { mensagem: "Olá" }.
         Assim, funções que leem msg.payload.mensagem / msg.payload.comando funcionam sem nenhuma alteração.
       • Antes era enviado JSON como text/plain; o Node-RED entrega text/plain como TEXTO (string), e uma função que lê
         msg.payload.mensagem recebia undefined e respondia 400 ("mensagem vazia"). Esse era o erro do display OLED.
   - false: application/json (exige preflight: habilite httpNodeCors no settings.js do Node-RED ou use um back-end com CORS).

   [BACKEND] PONTO DE INTEGRAÇÃO nº 4: se o back-end exigir autenticação (token/cookie), inclua aqui o cabeçalho
   Authorization (ou credentials: 'include') — é o único lugar onde isso precisa ser feito. */
(function () {
  const CS = window.CampusSmart;

  /* kind: timeout | network | offline (503) | http (outros códigos).  detail: texto de erro devolvido pela API, se houver. */
  class ApiError extends Error {
    constructor(kind, status, detail) { super(kind); this.kind = kind; this.status = status || 0; this.detail = detail || ''; }
  }

  /* Objeto plano → "chave=valor&..." (valores convertidos em texto, com acentos e símbolos codificados). */
  const toForm = obj => new URLSearchParams(Object.entries(obj).map(([k, v]) => [k, v === null || v === undefined ? '' : String(v)])).toString();

  /* Lê a mensagem de erro que a API costuma devolver ({erro: "..."} ou {message: "..."}). Nunca falha. */
  async function readErrorDetail(res) {
    try {
      const j = await res.json();
      const d = j && (j.erro || j.error || j.mensagem || j.message);
      return typeof d === 'string' ? d.slice(0, 160) : '';
    } catch { return ''; }
  }

  async function request(path, { method = 'GET', body } = {}) {
    const cfg = CS.config;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), cfg.TIMEOUT_MS);
    const headers = { Accept: 'application/json' };
    let payload;
    if (body !== undefined) {
      if (cfg.SIMPLE_REQUESTS) { headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8'; payload = toForm(body); }
      else { headers['Content-Type'] = 'application/json'; payload = JSON.stringify(body); }
    }
    let res;
    try {
      res = await fetch(cfg.API_BASE + path, { method, headers, body: payload, signal: ctrl.signal });
    } catch (err) {
      throw new ApiError(err.name === 'AbortError' ? 'timeout' : 'network');
    } finally { clearTimeout(timer); }
    if (!res.ok) throw new ApiError(res.status === 503 ? 'offline' : 'http', res.status, await readErrorDetail(res));
    try { return await res.json(); } catch { return {}; }
  }

  CS.services.http = { request, ApiError, toForm };
})();
