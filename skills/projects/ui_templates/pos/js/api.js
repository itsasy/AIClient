import { API_BASE, SEND_AUTH_HEADER } from "./config.js";
import { session } from "./state.js";

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const token = session.token();
  if (token && SEND_AUTH_HEADER) headers.set("X-Auth-Token", token);
  const response = await fetch(API_BASE + path, { ...options, headers });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `API ${response.status}`);
  return data;
}

export const json = (method, body) => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  config: { modules: () => request("/api/config/modules") },
  health: () => request("/api/health"),
  auth: {
    login: (email, password) => request("/api/auth/login", json("POST", { email, password })),
    me: () => request("/api/auth/me"),
    logout: () => request("/api/auth/logout", json("POST", { token: session.token() })),
  },
  patients: {
    list: () => request("/api/patients"),
    get: (id) => request(`/api/patients/${id}`),
    create: (item) => request("/api/patients", json("POST", item)),
  },
  agenda: {
    list: (patient_id) => request(`/api/agenda?patient_id=${patient_id ?? ""}`),
    create: (item) => request("/api/agenda", json("POST", item)),
    status: (id, status) => request(`/api/agenda/${id}/status`, json("POST", { status })),
  },
  odontogram: {
    get: (patient_id) => request(`/api/odontogram/${patient_id}`),
    finding: (patient_id, finding) => request(`/api/odontogram/${patient_id}/finding`, json("POST", finding)),
  },
  clinicalHistory: {
    list: (patient_id) => request(`/api/patients/${patient_id}/history`),
    add: (patient_id, content) => request(`/api/patients/${patient_id}/history`, json("POST", { content })),
  },
  prescriptions: {
    list: () => request("/api/prescriptions"),
    create: (item) => request("/api/prescriptions", json("POST", item)),
  },
  catalog: {
    list: () => request("/api/catalog"),
    create: (item) => request("/api/catalog", json("POST", item)),
    update: (sku, data) => request(`/api/catalog/${sku}`, json("PUT", data)),
  },
  sales: {
    sell: (items, method, currency, idempotency_key) => request("/api/sell", json("POST", { items, method, currency, idempotency_key })),
    history: () => request("/api/sales/history"),
  },
  cash: {
    status: () => request("/api/cash/status"),
    open: (amount) => request("/api/cash/open", json("POST", { amount })),
    close: () => request("/api/cash/close", json("POST", {})),
  },
  delivery: {
    list: () => request("/api/delivery"),
    create: (item) => request("/api/delivery", json("POST", item)),
    status: (id, status) => request(`/api/delivery/${id}/status`, json("POST", { status })),
  },
  reports: {
    summary: () => request("/api/reports/summary"),
  },
  inventory: {
    list: () => request("/api/inventory"),
    adjust: (sku, qty, reason) => request("/api/inventory/adjust", json("POST", { sku, qty, reason })),
  },
  restaurant: {
    snapshot: () => request("/api/restaurant/snapshot"),
  },
};
