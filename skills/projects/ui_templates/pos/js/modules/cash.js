
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderCaja } from "../views/caja.js";

const cashApi = {
  cash: {
    get: () => request("/api/cash"),
    open: (initial) => request("/api/cash/open", json("POST", { initial })),
    close: () => request("/api/cash/close", { method: "POST" }),
    movement: (amount, description) => request("/api/cash/movement", json("POST", { amount, description })),
  }
};

Registry.register({
  id: 'cash',
  api: cashApi,
  menu: { title: 'OPERACION', items: [
    { view: 'caja', label: 'Caja' }
  ]},
  routes: {
    'caja': (outlet) => renderCaja(outlet, () => Registry.routes['caja'](outlet))
  }
});
