import { login } from "./auth.js";

const form    = document.querySelector("#loginForm");
const message = document.querySelector("#loginMsg");
const button  = document.getElementById("loginBtn");

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  button.disabled     = true;
  button.textContent  = "Ingresando…";
  message.className   = "msg";
  message.textContent = "";
  try {
    await login(form.email.value, form.password.value);
    window.location.href = "/";           // Ruta del servidor Flask
  } catch (error) {
    message.className   = "msg err";
    message.textContent = error.message || "API offline";
    button.disabled     = false;
    button.textContent  = "Iniciar sesión";
  }
});
