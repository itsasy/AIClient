
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderHistorial } from "../views/historial.js";

const historyApi = {
  history: {
    list: () => request("/api/sales/history?limit=50"),
    void: (id, reason) => request(`/api/sales/history/${id}/void`, json("POST", { reason })),
  }
};

Registry.register({
  id: 'history',
  api: historyApi,
  menu: { title: 'GESTION', items: [
    { view: 'historial', label: 'Historial' }
  ]},
  routes: {
    'historial': (outlet) => renderHistorial(outlet, () => Registry.routes['historial'](outlet))
  }
});
