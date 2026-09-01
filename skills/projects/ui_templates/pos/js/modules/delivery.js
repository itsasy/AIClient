
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderDelivery } from "../views/delivery.js";

const deliveryApi = {
  delivery: {
    list: () => request("/api/delivery"),
    create: (address, note) => request("/api/delivery", json("POST", { address, note, status: "pendiente" })),
    status: (id, status) => request(`/api/delivery/${id}/status`, json("POST", { status })),
  }
};

Registry.register({
  id: 'delivery',
  api: deliveryApi,
  menu: { title: 'OPERACION', items: [
    { view: 'delivery', label: 'Delivery' }
  ]},
  routes: {
    'delivery': (outlet) => renderDelivery(outlet, () => Registry.routes['delivery'](outlet))
  }
});
