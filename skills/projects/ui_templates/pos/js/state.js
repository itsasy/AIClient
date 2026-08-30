import { TOKEN_KEY, USER_KEY } from "./config.js";

export const session = {
  token: () => localStorage.getItem(TOKEN_KEY) || "",
  user: () => localStorage.getItem(USER_KEY) || "",
  save: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, user);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },
};
