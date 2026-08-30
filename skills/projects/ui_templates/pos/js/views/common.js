import { escapeHtml, loading, errorView } from "../components.js";

export async function renderAsync(outlet, label, loader, render) {
  const version = (Number(outlet.dataset.renderVersion) || 0) + 1;
  outlet.dataset.renderVersion = String(version);
  outlet.innerHTML = loading(label);
  try {
    const data = await loader();
    if (outlet.dataset.renderVersion === String(version)) render(data);
  } catch (error) {
    if (outlet.dataset.renderVersion === String(version)) outlet.innerHTML = errorView(error.message || "API offline");
  }
}

export const tableEmpty = (columns) => `<tr><td colspan="${columns}">—</td></tr>`;
export { escapeHtml };
