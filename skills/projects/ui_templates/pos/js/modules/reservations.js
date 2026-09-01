
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderReservations } from "../views/reservations.js";

Registry.register({
  id: 'reservations',
  api: {
    reservations: { list: () => request("/api/reservations"), create: (item) => request("/api/reservations", json("POST", item)) }
  },
  menu: { title: 'GESTION', items: [
    { view: 'reservations', label: 'Reservas' }
  ]},
  routes: {
    'reservations': (outlet) => renderReservations(outlet, () => Registry.routes['reservations'](outlet))
  }
});
