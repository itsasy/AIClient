
import { Registry } from "../registry.js";
import { request } from "../api.js";
import { renderRestaurant } from "../views/restaurant.js";

Registry.register({
  id: 'restaurant',
  api: { restaurant: { snapshot: () => request("/api/restaurant/snapshot") } },
  menu: { title: 'RESTAURANT', items: [
    { view: 'restaurant', label: 'Dashboard' }
  ]},
  routes: {
    'restaurant': (outlet) => renderRestaurant(outlet, () => Registry.routes['restaurant'](outlet))
  }
});
