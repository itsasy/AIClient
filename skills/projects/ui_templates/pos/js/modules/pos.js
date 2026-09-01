
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderDashboard } from "../views/dashboard.js";

const posApi = {
  sales: {
    create: (items, method, currency, idempotency_key) => request("/api/sell", json("POST", { items, method, currency, idempotency_key })),
  }
};

Registry.register({
  id: 'pos',
  api: posApi,
  menu: { title: 'OPERACION', items: [
    { view: 'dashboard', label: 'Dashboard' },
    { view: 'pos-pay', label: 'Cobro / POS' }
  ]},
  routes: {
    'dashboard': (outlet) => renderDashboard(outlet, () => Registry.routes['dashboard'](outlet)),
    'pos-pay': (outlet) => {
      outlet.innerHTML = '';
      const frame = document.createElement('iframe');
      frame.src = 'pos-pay.html?embed=1';
      frame.title = 'Cobro POS';
      outlet.appendChild(frame);
    }
  }
});
