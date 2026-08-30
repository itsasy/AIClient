const runtime = globalThis.POS_SHELL_CONFIG || {};
const configuredBase = runtime.apiBase || localStorage.getItem("posApiBase") || "http://127.0.0.1:8765";

export const API_BASE = String(configuredBase).replace(/\/+$/, "");
export const TOKEN_KEY = runtime.tokenKey || "posAuthToken";
export const USER_KEY = runtime.userKey || "posAuthUser";

export const SEND_AUTH_HEADER = Boolean(runtime.apiBase) || (() => {
	try {
		const target = new URL(API_BASE, location.href);
		return ["127.0.0.1", "localhost", "::1"].includes(target.hostname);
	} catch {
		return false;
	}
})();
