import { api } from "../api.js";
import { money } from "../components.js";
import { renderAsync, escapeHtml } from "./common.js";

export function renderDashboard(outlet, refresh) {
  return renderAsync(outlet, "Cargando dashboard…", api.reports ? api.reports.summary : async () => ({}), (s) => {
    const cash=s.cash||{}; const statuses=Object.entries(s.deliveries_by_status||{}).map(([key,value])=>`${key}: ${value}`).join(" · ")||"sin envíos";
    outlet.innerHTML=`<div class="panel"><h1>Dashboard</h1><p class="hint">Resumen operativo · locale ${escapeHtml(s.locale)} · <button class="btn secondary" id="dashRefresh" type="button">Actualizar</button></p><div class="kpis"><div class="kpi"><div class="label">Productos</div><div class="value">${s.catalog_count??"—"}</div></div><div class="kpi"><div class="label">Caja</div><div class="value">${cash.is_open?"Abierta":"Cerrada"}</div></div><div class="kpi"><div class="label">Saldo</div><div class="value">${money(cash.balance)}</div></div><div class="kpi"><div class="label">Envíos</div><div class="value">${s.delivery_count??0}</div></div></div><div class="card"><h2>Delivery</h2><p class="hint">${escapeHtml(statuses)}</p></div></div>`;
    outlet.querySelector("#dashRefresh").addEventListener("click",refresh);
  });
}
