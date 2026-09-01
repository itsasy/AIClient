import { api } from "../api.js";
import { money } from "../components.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderReportes(outlet, refresh) {
  return renderAsync(outlet,"Cargando reportes…",api.reports.summary,(s)=>{const cash=s.cash||{};const rows=Object.entries(s.deliveries_by_status||{}).map(([status,count])=>`<tr><td>${escapeHtml(status)}</td><td>${count}</td></tr>`).join("")||tableEmpty(2);outlet.innerHTML=`<div class="panel"><h1>Reportes</h1><p class="hint">Resumen demo · locale ${escapeHtml(s.locale)}</p><div class="kpis"><div class="kpi"><div class="label">Productos</div><div class="value">${s.catalog_count??"—"}</div></div><div class="kpi"><div class="label">Caja</div><div class="value">${cash.is_open?"Abierta":"Cerrada"}</div></div><div class="kpi"><div class="label">Saldo</div><div class="value">${money(cash.balance)}</div></div><div class="kpi"><div class="label">Envíos</div><div class="value">${s.delivery_count??0}</div></div></div><button class="btn secondary" id="repRefresh" type="button">Actualizar</button><div class="card"><h2>Delivery por estado</h2><table><thead><tr><th>Estado</th><th>Cantidad</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;outlet.querySelector("#repRefresh").addEventListener("click",refresh);});
}
