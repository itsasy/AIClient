import { API_BASE } from "./config.js";
import { api } from "./api.js";
import { ensureSession } from "./auth.js";
import { escapeHtml, money } from "./components.js";

const payButton = document.querySelector("#pay");
const status = document.querySelector("#status");
const badge = document.querySelector("#apiBadge");
const picker = document.querySelector("#productPicker");
const currencySelect = document.querySelector("#currency");
const lines = document.querySelector("#lines");
const totalElement = document.querySelector("#total");

let method = "efectivo";
let currency = "ARS";
let products = [];
const cart = new Map();
let idempotencyKey = crypto.randomUUID();

function calculateTotal() {
  return [...cart.entries()].reduce((sum, [sku, quantity]) => {
    const product = products.find((item) => item.sku === sku);
    return sum + Number(product?.precio || 0) * Number(quantity || 0);
  }, 0);
}

function renderCart() {
  if (!lines) return;

  if (cart.size === 0) {
    lines.innerHTML = `
      <tr>
        <td colspan="5">No hay productos seleccionados</td>
      </tr>
    `;

    totalElement.textContent = money(0);
    payButton.disabled = true;
    return;
  }

  lines.innerHTML = [...cart.entries()]
    .map(([sku, quantity]) => {
      const product = products.find((item) => item.sku === sku);
      const name = product?.nombre || sku;
      const price = Number(product?.precio || 0);
      const subtotal = price * Number(quantity || 0);

      return `
        <tr>
          <td>${escapeHtml(sku)}</td>
          <td>${escapeHtml(name)}</td>
          <td>
            <input
              class="cart-quantity"
              data-sku="${escapeHtml(sku)}"
              type="number"
              min="0"
              step="1"
              value="${Number(quantity)}"
              aria-label="Cantidad de ${escapeHtml(name)}"
            />
          </td>
          <td>${money(price)}</td>
          <td>${money(subtotal)}</td>
        </tr>
      `;
    })
    .join("");

  totalElement.textContent = money(calculateTotal());
  payButton.disabled = false;

  lines.querySelectorAll(".cart-quantity").forEach((input) => {
    input.addEventListener("change", () => {
      const sku = input.dataset.sku;
      const quantity = Number(input.value || 0);

      if (!sku) return;

      if (quantity <= 0) {
        cart.delete(sku);
      } else {
        cart.set(sku, quantity);
      }

      renderCart();
    });
  });
}

async function loadProducts() {
  const data = await api.catalog.list();

  products = Array.isArray(data)
    ? data
    : data.items || [];

  picker.innerHTML = "";

  if (products.length === 0) {
    picker.innerHTML = `
      <option value="">No hay productos disponibles</option>
    `;

    cart.clear();
    renderCart();
    return;
  }

  picker.innerHTML = `
    <option value="">Seleccionar producto...</option>
    ${products
      .map(
        (product) => `
          <option value="${escapeHtml(product.sku)}">
            ${escapeHtml(product.nombre)} · ${money(product.precio)}
          </option>
        `,
      )
      .join("")}
  `;

  picker.value = "";
  renderCart();
}

picker.addEventListener("change", () => {
  const sku = picker.value;

  if (!sku) return;

  cart.set(sku, (cart.get(sku) || 0) + 1);

  renderCart();

  // Permite volver a seleccionar el mismo producto.
  picker.value = "";
});

document.querySelectorAll("[data-method]").forEach((button) => {
  button.addEventListener("click", () => {
    method = button.dataset.method || "efectivo";

    document.querySelectorAll("[data-method]").forEach((item) => {
      item.classList.toggle("active", item === button);
    });
  });
});

currencySelect.addEventListener("change", (event) => {
  currency = event.target.value || "ARS";
});

payButton.addEventListener("click", async () => {
  if (cart.size === 0) {
    status.className = "err";
    status.textContent = "Agrega al menos un producto.";
    return;
  }

  payButton.disabled = true;
  status.className = "";
  status.textContent = "Procesando...";

  try {
    // api.js expone sales.sell(), no sales.create().
    const data = await api.sales.sell(
      [...cart.entries()],
      method,
      currency,
      idempotencyKey,
    );

    if (!data.ok) {
      throw new Error(data.error || "Pago rechazado");
    }

    status.className = "ok";

    const paymentId =
      data.payment?.payment_id ||
      data.payment?.id ||
      "";

    status.textContent = [
      `OK ${data.total ?? ""}`,
      paymentId,
      data.estado || "",
      data.cash_balance !== undefined
        ? `caja ${data.cash_balance}`
        : "",
    ]
      .filter(Boolean)
      .join(" · ");

    // Nueva clave solamente después de una venta exitosa.
    idempotencyKey = crypto.randomUUID();

    cart.clear();
    renderCart();
  } catch (error) {
    status.className = "err";
    status.textContent = `Error: ${error.message}`;
  } finally {
    payButton.disabled = cart.size === 0;
  }
});

payButton.disabled = true;

ensureSession().then((valid) => {
  if (!valid) {
    status.className = "err";
    status.textContent = "Sesión requerida para cobrar";
    return;
  }

  loadProducts().catch((error) => {
    status.className = "err";
    status.textContent = error.message;
  });
});

api.health()
  .then((data) => {
    badge.textContent = data.ok
      ? "API ok · mock"
      : "API offline";
  })
  .catch(() => {
    badge.textContent = "API offline";
    badge.classList.add("off");
  });

if (new URLSearchParams(location.search).get("embed") === "1") {
  document.documentElement.classList.add("embed");

  const headerLink = document.querySelector(".pos-header a");

  if (headerLink) {
    headerLink.hidden = true;
  }
}

export { API_BASE };
