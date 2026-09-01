import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderAgenda(outlet, refresh, fixedPatientId = null) {
  const loadFunc = () => api.agenda.list(fixedPatientId);

  return renderAsync(
    outlet,
    "Cargando agenda...",
    loadFunc,
    (data) => {
      const rows =
        (data.items || [])
          .map(
            (item) => `
              <tr>
                <td>${escapeHtml(item.id)}</td>
                <td>${escapeHtml(item.patient_id)}</td>
                <td>${escapeHtml(item.starts_at)}</td>
                <td>${escapeHtml(item.status)}</td>
                <td>${escapeHtml(item.note || "")}</td>
                <td>
                  <button
                    class="btn secondary action-btn"
                    data-id="${escapeHtml(item.id)}"
                    data-status="confirmed"
                    type="button"
                  >
                    Confirmar
                  </button>

                  <button
                    class="btn secondary action-btn"
                    data-id="${escapeHtml(item.id)}"
                    data-status="cancelled"
                    type="button"
                  >
                    Cancelar
                  </button>
                </td>
              </tr>
            `,
          )
          .join("") || tableEmpty(6);

      const pidInput = fixedPatientId
        ? `<input type="hidden" id="agPatientId" value="${escapeHtml(fixedPatientId)}">`
        : `
          <label>
            Paciente ID
            <input id="agPatientId" required>
          </label>
        `;

      outlet.innerHTML = `
        <div class="panel">
          <div class="card" style="margin-bottom:20px;">
            <div class="row">
              ${pidInput}

              <label>
                Fecha/Hora
                <input
                  id="agStartsAt"
                  type="datetime-local"
                  required
                >
              </label>

              <label style="flex-grow:1">
                Nota
                <input id="agNote">
              </label>
            </div>

            <div style="margin-top:10px;">
              <button class="btn" id="agAdd" type="button">
                Crear turno
              </button>

              <button
                class="btn secondary"
                id="agRefresh"
                type="button"
              >
                Actualizar
              </button>
            </div>
          </div>

          <p class="msg" id="agMsg" role="status"></p>

          <div class="card">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Paciente</th>
                  <th>Inicio</th>
                  <th>Estado</th>
                  <th>Nota</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                ${rows}
              </tbody>
            </table>
          </div>
        </div>
      `;

      outlet
        .querySelector("#agRefresh")
        ?.addEventListener("click", refresh);

      outlet
        .querySelector("#agAdd")
        ?.addEventListener("click", async () => {
          const msg = outlet.querySelector("#agMsg");

          msg.className = "msg";
          msg.textContent = "";

          try {
            await api.agenda.create({
              patient_id: outlet.querySelector("#agPatientId").value,
              starts_at: outlet.querySelector("#agStartsAt").value,
              note: outlet.querySelector("#agNote").value,
            });

            await refresh();
          } catch (error) {
            msg.className = "msg err";
            msg.textContent = error.message;
          }
        });

      outlet.querySelectorAll(".action-btn").forEach((button) => {
        button.addEventListener("click", async () => {
          const id = button.dataset.id;
          const status = button.dataset.status;

          try {
            await api.agenda.status(id, status);
            await refresh();
          } catch (error) {
            const msg = outlet.querySelector("#agMsg");
            msg.className = "msg err";
            msg.textContent = error.message;
          }
        });
      });
    },
  );
}
