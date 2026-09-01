import { api } from "../api.js";
import { escapeHtml, renderAsync, tableEmpty } from "./common.js";

export function renderClinicalHistory(outlet, patient_id) {
  const load = () => renderAsync(outlet, 'Cargando historia clínica...', () => api.clinicalHistory.list(patient_id), (data) => {
    const rows = (data.items || []).map(n => `<tr>
      <td>${escapeHtml(n.created_at || '')}</td>
      <td>${escapeHtml(n.author || '')}</td>
      <td>${escapeHtml(n.content || '')}</td>
    </tr>`).join('') || tableEmpty(3);
    
    outlet.innerHTML = `<div class="card" style="margin-bottom:20px;">
        <h2>Nueva Evolución</h2>
        <textarea id="evoContent" rows="3" style="width:100%; margin-bottom:10px;"></textarea>
        <button class="btn" id="btnSaveEvo">Guardar Evolución</button>
        <p id="evoMsg" class="msg"></p>
      </div>
      <div class="card">
        <h2>Evoluciones Anteriores</h2>
        <table>
          <thead><tr><th>Fecha</th><th>Autor</th><th>Contenido</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
    
    outlet.querySelector('#btnSaveEvo').addEventListener('click', async () => {
      const content = outlet.querySelector('#evoContent').value.trim();
      const msg = outlet.querySelector('#evoMsg');
      if (!content) return;
      try {
        await api.clinicalHistory.add(patient_id, content);
        load();
      } catch (e) {
        msg.className = 'msg err';
        msg.textContent = e.message;
      }
    });
  });
  
  load();
}
