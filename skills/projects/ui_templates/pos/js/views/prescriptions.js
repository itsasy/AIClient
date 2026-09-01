import { api } from "../api.js";
import { renderAsync, escapeHtml, tableEmpty } from "./common.js";

export function renderPrescriptions(outlet, refresh, fixedPatientId = null) {
  // If api.prescriptions.list doesn't natively support filtering by ID, we filter client side
  const loadFunc = async () => {
    const res = await api.prescriptions.list();
    if (fixedPatientId && res.items) {
      res.items = res.items.filter(i => String(i.patient_id) === String(fixedPatientId));
    }
    return res;
  };
  
  return renderAsync(outlet, "Cargando prescripciones...", loadFunc, (data) => {
    const rows = (data.items || []).map((item) => `<tr>
      <td>${escapeHtml(item.id || '')}</td>
      <td>${escapeHtml(item.patient_id || '')}</td>
      <td>${escapeHtml(item.medication || '')}</td>
      <td>${escapeHtml(item.instructions || '')}</td>
    </tr>`).join("") || tableEmpty(4);
    
    const pidInput = fixedPatientId 
      ? `<input type="hidden" id="rxPatient" value="${fixedPatientId}">` 
      : `<label>Paciente<input id="rxPatient" required></label>`;
      
    outlet.innerHTML = `<div class="panel">
      <div class="card" style="margin-bottom:20px;">
        <div class="row">
          ${pidInput}
          <label>Medicamento<input id="rxMedication" required></label>
          <label style="flex-grow:1">Indicaciones<input id="rxInstructions"></label>
        </div>
        <div style="margin-top:10px;">
          <button class="btn" id="rxAdd" type="button">Crear receta</button>
        </div>
      </div>
      <p class="msg" id="rxMsg" role="status"></p>
      <div class="card">
        <table>
          <thead><tr><th>ID</th><th>Paciente</th><th>Medicamento</th><th>Indicaciones</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </div>`;
    
    if (!fixedPatientId) {
      outlet.querySelector("#rxRefresh").addEventListener("click", refresh);
    }
    
    outlet.querySelector("#rxAdd").addEventListener("click", async () => { 
      const msg = outlet.querySelector("#rxMsg"); 
      msg.textContent = '';
      try { 
        await api.prescriptions.create({ 
          patient_id: outlet.querySelector("#rxPatient").value, 
          medication: outlet.querySelector("#rxMedication").value, 
          instructions: outlet.querySelector("#rxInstructions").value 
        }); 
        refresh(); 
      } catch (error) { 
        msg.className = "msg err"; 
        msg.textContent = error.message; 
      } 
    });
  });
}
