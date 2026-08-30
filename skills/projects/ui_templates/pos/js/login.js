import { login } from "./auth.js";

const form = document.querySelector("#loginForm");
const message = document.querySelector("#loginMsg");
const button = form.querySelector("button[type=submit]");
form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled = true;
  message.className = "msg";
  message.textContent = "Procesando…";
  try {
    await login(form.email.value, form.password.value);
    location.href = "shell.html";
  } catch (error) {
    message.className = "msg err";
    message.textContent = error.message || "API offline";
    button.disabled = false;
  }
});
