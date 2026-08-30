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
  }
};
