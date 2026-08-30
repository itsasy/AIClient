import { API_BASE } from "./config.js";
import { api } from "./api.js";
import { ensureSession, login, logout } from "./auth.js";
import { session } from "./state.js";
import { currentView, navigate } from "./router.js";
import { Registry } from "./registry.js";

const outlet = document.querySelector("#outlet");
const navs = [];
const badge = document.querySelector("#apiBadge");
const chip = document.querySelector("#userChip");

function locked(value) { document.querySelector("#appShell").classList.toggle("locked", value); document.querySelector("#logoutBtn").hidden = value; chip.hidden = value; }
function showLogin() { locked(true); outlet.innerHTML = `<div class="panel login-gate"><h1>Iniciar sesión</h1><p class="hint">Ingrese sus credenciales</p><p id="loginMsg" class="msg" role="status"></p><div class="card"><label for="loginUser">Usuario</label><input id="loginUser" autocomplete="username"><label for="loginPass">Contraseña</label><input id="loginPass" type="password" autocomplete="current-password"><button class="btn" id="loginBtn" type="button">Entrar</button></div></div>`; outlet.querySelector("#loginBtn").addEventListener("click", async () => { const msg=outlet.querySelector("#loginMsg"); try { await login(outlet.querySelector("#loginUser").value, outlet.querySelector("#loginPass").value); locked(false); render(); } catch(e) { msg.className="msg err"; msg.textContent=e.message; } }); }

function render() { 
  const view = currentView(); 
  navs.forEach((nav) => nav.classList.toggle("active", nav.dataset.view === view)); 
  if (Registry.routes[view]) {
    Registry.routes[view](outlet);
  } else {
    outlet.innerHTML = '<div class="panel"><h1>404</h1><p>Módulo no cargado o ruta inexistente.</p></div>';
  }
}

async function loadModules() {
  let modules = {};
  try {
    const res = await api.config.modules();
    if(res.ok) modules = res.modules;
  } catch(e) {
    console.warn('Could not load modules config, fallback to empty', e);
  }
  
  // Mapping of config flags to module filenames
  const flagMap = {
    'enable_pos': 'pos',
    'enable_cash': 'cash',
    'enable_catalog': 'catalog',
    'enable_history': 'history',
    'enable_inventory': 'inventory',
    'enable_delivery': 'delivery',
    'enable_reports': 'reports',
    'enable_prescriptions': 'dental', // mapped to dental bundle
    'enable_reservations': 'reservations',
    'enable_tasks': 'tasks',
    'enable_restaurant': 'restaurant',
    'enable_dental': 'dental',
    'enable_patients': 'dental',
    'enable_agenda': 'dental'
  };
  
  const toLoad = new Set();
  for (const [flag, enabled] of Object.entries(modules)) {
    if (enabled && flagMap[flag]) toLoad.add(flagMap[flag]);
  }
  
  for (const mod of toLoad) {
    try {
      await import('./modules/' + mod + '.js');
    } catch(e) {
      console.warn('Failed to load module:', mod, e);
    }
  }
}

async function buildSidebar() {
  const sidebar = document.querySelector('#sidebarMenu');
  if(!sidebar) return;
  sidebar.innerHTML = '<strong>POS &middot; Plan</strong>';
  
  // Create sections grouped by title
  const grouped = {};
  for (const menu of Registry.menus) {
    if (!grouped[menu.title]) grouped[menu.title] = [];
    grouped[menu.title].push(...menu.items);
  }
  
  // Render
  for (const [title, items] of Object.entries(grouped)) {
    // skip duplicates
    const uniqueItems = [];
    const seen = new Set();
    for(const item of items) { if(!seen.has(item.view)) { seen.add(item.view); uniqueItems.push(item); } }
    
    if (uniqueItems.length === 0) continue;
    
    const div = document.createElement('div');
    div.className = 'section';
    div.textContent = title;
    sidebar.appendChild(div);
    
    for (const item of uniqueItems) {
      const btn = document.createElement('button');
      btn.className = 'nav';
      btn.dataset.view = item.view;
      btn.type = 'button';
      btn.textContent = item.label;
      btn.addEventListener('click', async () => {
        if(await ensureSession()) navigate(btn.dataset.view);
        else showLogin();
      });
      sidebar.appendChild(btn);
    }
  }
  
  navs.length = 0;
  navs.push(...document.querySelectorAll('.nav'));
}

async function checkHealth() { try { const data=await api.health(); badge.textContent=data.ok?"✓ API ok":"✗ API offline"; badge.className=data.ok?"ok":"err"; } catch { badge.textContent="✗ API offline"; badge.className="err"; } }

window.addEventListener("hashchange", () => { if(session.token()) render(); });
document.querySelector("#logoutBtn").addEventListener("click", async () => { await logout(); showLogin(); });

(async() => { 
  chip.textContent = session.user(); 
  checkHealth(); 
  
  await loadModules();
  await buildSidebar();
  
  if(await ensureSession()){ locked(false); render(); } else showLogin(); 
})();

export { API_BASE };
