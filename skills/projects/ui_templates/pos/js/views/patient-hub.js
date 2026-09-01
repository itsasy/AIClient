import { api } from "../api.js";
import { escapeHtml, renderAsync } from "./common.js";
import { renderOdontogram } from "./odontogram.js";
import { renderClinicalHistory } from "./clinical_history.js";
import { renderAgenda } from "./agenda.js";
import { renderPrescriptions } from "./prescriptions.js";

export function renderPatientHub(outlet) {
  const params = new URLSearchParams(location.hash.split('?')[1] || '');
  const pid = params.get('id');
  
  if (!pid) {
    outlet.innerHTML = '<div class="panel"><p class="msg err">No se especificó paciente.</p></div>';
    return;
  }
  
  // First load patient data
  return renderAsync(outlet, 'Cargando paciente...', () => api.patients.get(pid), (data) => {
    const patient = data.item;
    outlet.innerHTML = `<div class="panel">
      <h1>Portal del Paciente</h1>
      <p class="hint">Paciente: <strong>${escapeHtml(patient.nombre)}</strong> (ID: ${patient.id}) | Documento: ${escapeHtml(patient.documento)} | Tel: ${escapeHtml(patient.telefono)}</p>
      
      <div class="tabs" style="margin-bottom: 20px; display:flex; gap:10px;">
        <button class="btn secondary" data-tab="datos">Datos</button>
        <button class="btn secondary" data-tab="history">Historia Clínica</button>
        <button class="btn secondary" data-tab="odontogram">Odontograma</button>
        <button class="btn secondary" data-tab="agenda">Turnos</button>
        <button class="btn secondary" data-tab="recetas">Recetas</button>
      </div>
      <div id="hubOutlet"></div>
    </div>`;
    
    const hubOutlet = outlet.querySelector('#hubOutlet');
    const tabs = outlet.querySelectorAll('.tabs button');
    
    function switchTab(tab) {
      tabs.forEach(t => t.className = 'btn ' + (t.dataset.tab === tab ? 'primary' : 'secondary'));
      if (tab === 'datos') {
        hubOutlet.innerHTML = `<div class="card">
            <h2>Datos del Paciente</h2>
            <p><strong>Nombre:</strong> ${escapeHtml(patient.nombre)}</p>
            <p><strong>Documento:</strong> ${escapeHtml(patient.documento)}</p>
            <p><strong>Teléfono:</strong> ${escapeHtml(patient.telefono)}</p>
          </div>
        `;
      } else if (tab === 'history') {
        renderClinicalHistory(hubOutlet, pid);
      } else if (tab === 'odontogram') {
        renderOdontogram(hubOutlet, pid);
      } else if (tab === 'agenda') {
        renderAgenda(hubOutlet, () => switchTab('agenda'), pid);
      } else if (tab === 'recetas') {
        renderPrescriptions(hubOutlet, () => switchTab('recetas'), pid);
      }
    }
    
    tabs.forEach(btn => btn.addEventListener('click', () => switchTab(btn.dataset.tab)));
    switchTab('datos'); // default tab
  });
}
