import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderReservations(outlet, refresh) {
  return renderAsync(outlet, "Cargando reservas…", api.reservations.list, (data) => {
    const rows = (data.items || []).map((item) => `<tr><td>${escapeHtml(item.id)}</td><td>${escapeHtml(item.customer)}</td><td>${escapeHtml(item.starts_at)}</td><td>${escapeHtml(item.status)}</td></tr>`).join("") || tableEmpty(4);
    outlet.innerHTML = `<div class="panel"><h1>Reservas</h1><p class="hint">Reservas disponibles vía API.</p><div class="row"><label>Cliente<input id="reservationCustomer" required></label><label>Inicio<input id="reservationStartsAt" type="datetime-local" required></label><label>Estado<input id="reservationStatus" value="pending"></label><button class="btn" id="reservationAdd" type="button">Crear reserva</button><button class="btn secondary" id="reservationRefresh" type="button">Actualizar</button></div><p class="msg" id="reservationMsg" role="status"></p><div class="card"><table><thead><tr><th>ID</th><th>Cliente</th><th>Inicio</th><th>Estado</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
    outlet.querySelector("#reservationRefresh").addEventListener("click", refresh);
    outlet.querySelector("#reservationAdd").addEventListener("click", async () => { const msg = outlet.querySelector("#reservationMsg"); try { await api.reservations.create({ customer: outlet.querySelector("#reservationCustomer").value, starts_at: outlet.querySelector("#reservationStartsAt").value, status: outlet.querySelector("#reservationStatus").value }); refresh(); } catch (error) { msg.className = "msg err"; msg.textContent = error.message; } });
  });
}
