import { api } from "./api.js";
import { session } from "./state.js";

export async function login(email, password) {
  const data = await api.auth.login(email, password);
  session.save(data.token, data.user);
  return data;
}

export async function ensureSession() {
  if (!session.token()) return false;
  try {
    await api.auth.me();
    return true;
  } catch {
    session.clear();
    return false;
  }
}

export async function logout() {
  try { await api.auth.logout(); } catch { /* local logout must work offline */ } finally { session.clear(); }
}
