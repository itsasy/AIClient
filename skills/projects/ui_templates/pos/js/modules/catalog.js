
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderProductos } from "../views/productos.js";

const catalogApi = {
  catalog: {
    list: () => request("/api/catalog"),
    add: (item) => request("/api/catalog", json("POST", item)),
  }
};

Registry.register({
  id: 'catalog',
  api: catalogApi,
  menu: { title: 'CATALOGO', items: [
    { view: 'productos', label: 'Productos' }
  ]},
  routes: {
    'productos': (outlet) => renderProductos(outlet, () => Registry.routes['productos'](outlet))
  }
});
