/* Helpers de marcação. Todo texto vindo de dados passa por esc() (protege contra HTML injetado por uma API futura). */
(function () {
  const CS = window.CampusSmart;
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const priorityTag = (level, label) => `<span class="priority ${esc(level)}">${esc(String(label).toUpperCase())}</span>`;
  const loadingBox = text => `<div class="state-box" role="status"><div class="spinner"></div><p>${esc(text)}</p></div>`;
  const errorBox = (title, text, action) => `<div class="state-box error" role="alert"><div class="state-icon">✕</div><b>${esc(title)}</b><p>${esc(text)}</p>${action || ''}</div>`;
  const emptyBox = (title, text) => `<div class="state-box empty"><div class="state-icon ok">✓</div><b>${esc(title)}</b><p>${esc(text)}</p></div>`;
  const setHtml = (el, html) => { if (el._last !== html) { el.innerHTML = html; el._last = html; } };
  CS.ui.html = { setHtml, esc, priorityTag, loadingBox, errorBox, emptyBox };
})();
