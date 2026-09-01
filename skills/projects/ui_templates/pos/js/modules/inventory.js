import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderInventory } from "../views/inventory.js";

const inventoryApi = {
  inventory: {
    list: () => request("/api/inventory"),

    move: (type, payload = {}) =>
      request(
        "/api/inventory/adjust",
        json("POST", {
          ...payload,
          type,
        }),
      ),

    kardex: (sku) =>
      request(
        `/api/inventory/${encodeURIComponent(sku)}/movements`,
      ),
  },
};

Registry.register({
  id: "inventory",
  api: inventoryApi,
  menu: {
    title: "OPERACION",
    items: [
      {
        view: "inventory",
        label: "Inventario",
      },
    ],
  },
  routes: {
    inventory: (outlet) => renderInventory(outlet),
  },
});
