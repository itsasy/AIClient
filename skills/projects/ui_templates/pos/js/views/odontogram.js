import { api } from "../api.js";
import { escapeHtml, renderAsync } from "./common.js";

const TOOTH_GRID = [
  [18, 17, 16, 15, 14, 13, 12, 11],
  [21, 22, 23, 24, 25, 26, 27, 28],
  [48, 47, 46, 45, 44, 43, 42, 41],
  [31, 32, 33, 34, 35, 36, 37, 38]
];

function isAnterior(t) { return (t % 10) >= 1 && (t % 10) <= 3; }

const COLORS = { sano: '#fff', caries: '#ff4d4f', obturacion: '#1890ff', fractura: '#faad14', endodoncia: '#eb2f96', corona: '#fadb14', ausente: '#000', implante: '#52c41a', extraccion: '#000', sellador: '#13c2c2' };

function getLegend() {
  return '<div style="display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin-bottom:20px; font-size:12px;">' + 
    Object.entries(COLORS).map(([k,v]) => `<div style="display:flex; align-items:center; gap:5px;"><div style="width:12px; height:12px; background:${v}; border:1px solid #ccc;"></div>${k}</div>`).join('') +
  '</div>';
}

function getToothSvg(t, state) {
  const isAnt = isAnterior(t);
  const color = (surf) => COLORS[state[surf]] || '#fff';
  let html = `<svg viewBox="0 0 100 100" width="40" height="40" style="cursor:pointer" class="tooth-svg" data-tooth="${t}">`;
  if (state['G'] === 'ausente' || state['G'] === 'extraccion') {
    html += `<line x1="10" y1="10" x2="90" y2="90" stroke="black" stroke-width="10" />`;
    html += `<line x1="90" y1="10" x2="10" y2="90" stroke="black" stroke-width="10" />`;
  } else {
    html += `<polygon points="10,10 90,10 75,25 25,25" fill="${color('V')}" stroke="#333" data-surf="V" />`;
    html += `<polygon points="25,75 75,75 90,90 10,90" fill="${color('L')}" stroke="#333" data-surf="L" />`;
    html += `<polygon points="10,10 25,25 25,75 10,90" fill="${color('M')}" stroke="#333" data-surf="M" />`;
    html += `<polygon points="75,25 90,10 90,90 75,75" fill="${color('D')}" stroke="#333" data-surf="D" />`;
    const centerSurf = isAnt ? 'I' : 'O';
    html += `<rect x="25" y="25" width="50" height="50" fill="${color(centerSurf)}" stroke="#333" data-surf="${centerSurf}" />`;
    html += `<circle cx="50" cy="50" r="10" fill="${color('R')}" stroke="#333" style="opacity:0.8" data-surf="R" />`;
    if (state['G']) html += `<circle cx="50" cy="50" r="45" fill="none" stroke="${COLORS[state['G']]}" stroke-width="4" />`;
  }
  html += `<text x="50" y="115" text-anchor="middle" fill="#333" font-size="30">${t}</text></svg>`;
  return html;
}

export function renderOdontogram(outlet, patient_id) {
  let modalHtml = `<div id="odoModal" style="display:none; position:fixed; top:20%; left:50%; transform:translateX(-50%); background:white; padding:20px; border:1px solid #ccc; box-shadow:0 0 10px rgba(0,0,0,0.5); z-index:100; min-width:300px;">
      <h3>Registrar Hallazgo</h3>
      <p>Pieza: <strong id="mdlTooth"></strong> - Superficie: <select id="mdlSurf" style="display:inline-block; width:auto; padding:2px;"></select></p>
      
      <div class="card" style="margin-bottom:10px;">
        <label>Hallazgo</label>
        <select id="mdlKind" style="width:100%; margin-bottom:10px;">
          <option value="sano">Sano</option><option value="caries">Caries</option><option value="obturacion">Obturación</option><option value="fractura">Fractura</option><option value="endodoncia">Endodoncia</option><option value="corona">Corona</option><option value="ausente">Ausente</option><option value="implante">Implante</option><option value="extraccion">Extracción</option><option value="sellador">Sellador</option>
        </select>
        <label>Nota</label><input type="text" id="mdlNote" style="width:100%">
      </div>
      <button class="btn" id="mdlSave">Guardar</button>
      <button class="btn secondary" id="mdlCancel">Cancelar</button>
      <p id="mdlErr" class="msg err"></p>
    </div>`;

  const load = () => renderAsync(outlet, 'Cargando odontograma...', () => api.odontogram.get(patient_id), (data) => {
    let html = `<div class="card" style="text-align:center; overflow-x:auto;">`;
    html += getLegend();
    
    html += `<div style="display:flex; justify-content:center; gap:5px; margin-bottom:20px;">`;
    [...TOOTH_GRID[0], ...TOOTH_GRID[1]].forEach(t => { const s = (data.teeth && data.teeth[t]) ? data.teeth[t].current_state : {}; html += `<div style="display:flex; flex-direction:column; align-items:center; margin-bottom:10px;">${getToothSvg(t, s)}</div>`; });
    html += `</div><div style="display:flex; justify-content:center; gap:5px;">`;
    [...TOOTH_GRID[2], ...TOOTH_GRID[3]].forEach(t => { const s = (data.teeth && data.teeth[t]) ? data.teeth[t].current_state : {}; html += `<div style="display:flex; flex-direction:column; align-items:center; margin-bottom:10px;">${getToothSvg(t, s)}</div>`; });
    html += `</div></div>` + modalHtml;
    
    outlet.innerHTML = html;
    
    outlet.querySelectorAll('svg.tooth-svg').forEach(svg => {
      svg.addEventListener('click', (e) => {
        const tooth = parseInt(svg.dataset.tooth, 10);
        let surf = e.target.dataset.surf || 'G';
        
        outlet.querySelector('#mdlTooth').textContent = tooth;
        const selSurf = outlet.querySelector('#mdlSurf');
        selSurf.innerHTML = '';
        
        // Populate valid surfaces
        const isAnt = isAnterior(tooth);
        const validSurfs = [
          {v:'V', l:'Vestibular'}, {v:'L', l:'Palatina/Lingual'}, {v:'M', l:'Mesial'}, {v:'D', l:'Distal'}, 
          isAnt ? {v:'I', l:'Incisal'} : {v:'O', l:'Oclusal'},
          {v:'R', l:'Raíz'}, {v:'G', l:'General'}
        ];
        
        validSurfs.forEach(vs => {
          const opt = document.createElement('option');
          opt.value = vs.v;
          opt.textContent = vs.l;
          if (vs.v === surf) opt.selected = true;
          selSurf.appendChild(opt);
        });
        
        outlet.querySelector('#odoModal').style.display = 'block';
        outlet.querySelector('#mdlErr').textContent = '';
      });
    });
    
    outlet.querySelector('#mdlCancel').addEventListener('click', () => outlet.querySelector('#odoModal').style.display = 'none');
    
    outlet.querySelector('#mdlSave').addEventListener('click', async () => {
      const msg = outlet.querySelector('#mdlErr');
      msg.textContent = '';
      try {
        await api.odontogram.finding(patient_id, { 
          tooth: parseInt(outlet.querySelector('#mdlTooth').textContent, 10), 
          surface: outlet.querySelector('#mdlSurf').value, 
          kind: outlet.querySelector('#mdlKind').value, 
          note: outlet.querySelector('#mdlNote').value 
        });
        outlet.querySelector('#odoModal').style.display = 'none';
        load();
      } catch (e) { msg.textContent = e.message; }
    });
  });
  
  load();
}
