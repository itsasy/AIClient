import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderPatients(outlet, refresh) {
  return renderAsync(outlet, "Cargando pacientes...", api.patients.list, (data) => {
    const rows = (data.items || []).map((item) => `<tr>
      <td>${escapeHtml(item.id)}</td>
      <td>${escapeHtml(item.nombre)}</td>
      <td>${escapeHtml(item.documento)}</td>
      <td>${escapeHtml(item.telefono)}</td>
      <td><a href="#/patient-hub?id=${escapeHtml(item.id)}">Abrir Ficha</a></td>
    </tr>`).join("") || tableEmpty(5);

    outlet.innerHTML = `<div class="panel">
      <h1>Pacientes</h1>
      <p class="hint">Pacientes vía API.</p>
      <div class="row">
        <label>Nombre<input id="patName" required></label>
        <label>Documento<input id="patDoc"></label>
        <label>Teléfono<input id="patPhone"></label>
        <button class="btn" id="patAdd" type="button">Crear Paciente</button>
        <button class="btn secondary" id="patRefresh" type="button">Actualizar</button>
      </div>
      <p class="msg" id="patMsg" role="status"></p>
      <div class="card">
        <table>
          <thead>
            <tr><th>ID</th><th>Nombre</th><th>Documento</th><th>Teléfono</th><th>Odontograma</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;

    outlet.querySelector("#patRefresh").addEventListener("click", refresh);
    outlet.querySelector("#patAdd").addEventListener("click", async () => {
      const msg = outlet.querySelector("#patMsg");
      try {
        await api.patients.create({
          nombre: outlet.querySelector("#patName").value,
          documento: outlet.querySelector("#patDoc").value,
          telefono: outlet.querySelector("#patPhone").value
        });
        refresh();
      } catch (error) {
        msg.className = "msg err";
        msg.textContent = error.message;
      }
    });
  });
}
