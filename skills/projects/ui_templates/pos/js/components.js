export const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
export const money = (value) => Number(value || 0).toLocaleString("es-AR", { maximumFractionDigits: 2 });
export const loading = (label) => `<div class="panel"><p class="hint">${escapeHtml(label)}</p></div>`;
export const errorView = (message) => `<div class="panel"><p class="msg err">${escapeHtml(message)}</p></div>`;
export const emptyRow = (columns) => `<tr><td colspan="${columns}">—</td></tr>`;
