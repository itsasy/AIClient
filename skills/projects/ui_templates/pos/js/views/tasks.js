import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderTasks(outlet, refresh) {
  return renderAsync(outlet, "Cargando tareas…", api.tasks.list, (data) => {
    const rows = (data.items || []).map((item) => `<tr><td>${escapeHtml(item.id)}</td><td>${escapeHtml(item.title)}</td><td>${escapeHtml(item.status)}</td><td><button class="btn secondary" data-task="${escapeHtml(item.id)}" data-status="completed" type="button">Completar</button></td></tr>`).join("") || tableEmpty(4);
    outlet.innerHTML = `<div class="panel"><h1>Tareas</h1><p class="hint">Tareas disponibles vía API.</p><div class="row"><label>Título<input id="taskTitle" required></label><label>Estado<input id="taskStatus" value="pending"></label><button class="btn" id="taskAdd" type="button">Crear tarea</button><button class="btn secondary" id="taskRefresh" type="button">Actualizar</button></div><p class="msg" id="taskMsg" role="status"></p><div class="card"><table><thead><tr><th>ID</th><th>Título</th><th>Estado</th><th></th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
    outlet.querySelector("#taskRefresh").addEventListener("click", refresh);
    outlet.querySelector("#taskAdd").addEventListener("click", async () => { const msg = outlet.querySelector("#taskMsg"); try { await api.tasks.create({ title: outlet.querySelector("#taskTitle").value, status: outlet.querySelector("#taskStatus").value }); refresh(); } catch (error) { msg.className = "msg err"; msg.textContent = error.message; } });
    outlet.querySelectorAll("[data-task]").forEach((button) => button.addEventListener("click", async () => { try { await api.tasks.status(button.dataset.task, button.dataset.status); refresh(); } catch (error) { const msg = outlet.querySelector("#taskMsg"); msg.className = "msg err"; msg.textContent = error.message; } }));
  });
}
