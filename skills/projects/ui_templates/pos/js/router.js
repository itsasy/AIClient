import { Registry } from "./registry.js";

export function currentView() {
  const hash = location.hash.slice(1);
  if (!hash) return "dashboard";
  // some aliases for legacy support if needed, or strict mapping
  if (hash === 'cobro' || hash === 'pos') return 'pos-pay';
  
  if (Registry.routes[hash]) return hash;
  
  // Default fallback if route not registered
  return "dashboard";
}

export function navigate(view) {
  location.hash = view === "dashboard" ? "dashboard" : view;
}
