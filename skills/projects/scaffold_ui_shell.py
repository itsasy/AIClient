from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config import Config
from core.execution_plan import ExecutionPlan
from core.execution_step import ExecutionStep
from skills.base import Skill


class ScaffoldUiShellSkill(Skill):
    """
    Genera plantillas UI mínimas tipo POS (login + shell + dashboard).

    No usa LLM. Solo escribe HTML/CSS de referencia o stubs React/Vue según param.
    Por defecto: static HTML para no forzar stack.
    """

    name = "scaffold_ui_shell"
    description = "Scaffold UI shell POS (login, layout, dashboard)."
    version = "1.0"
    capabilities = ("ui_scaffold", "pos_ui", "frontend_shell")

    def execute(
        self,
        plan: ExecutionPlan,
        step: ExecutionStep,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not plan.allows_write():
            return {"ok": False, "result": None, "error": "Escritura no permitida."}

        root = Path(getattr(Config, "TARGET_PROJECT_ROOT", Path.cwd()))
        base = root / "src" / "ui" / "pos_shell"
        base.mkdir(parents=True, exist_ok=True)

        files = {
            "login.html": self._LOGIN,
            "shell.html": self._SHELL,
            "dashboard.html": self._DASHBOARD,
            "pos.css": self._CSS,
            "README.md": self._README,
        }
        created: list[str] = []
        for name, content in files.items():
            path = base / name
            if path.exists():
                continue
            path.write_text(content.strip() + "\n", encoding="utf-8")
            created.append(str(path.relative_to(root)))

        return {
            "ok": True,
            "result": {
                "type": "ui_scaffold",
                "path": "src/ui/pos_shell",
                "created": created,
            },
            "error": None,
        }

    _README = """# POS UI Shell (referencia)
Plantillas estáticas inspiradas en un POS limpio (login card + sidebar + KPIs).
Adaptar a React/Vue/Next según el stack del proyecto.
"""

    _CSS = """
:root {
  --primary: #e11d2e;
  --primary-hover: #c41122;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --text: #1a1a1a;
  --muted: #6b7280;
  --border: #e5e7eb;
  --ok: #16a34a;
  --warn: #f59e0b;
  --radius: 12px;
  --shadow: 0 8px 30px rgba(0,0,0,.06);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
  background: var(--bg);
  color: var(--text);
}
.btn-primary {
  background: var(--primary);
  color: #fff;
  border: 0;
  border-radius: 10px;
  padding: 12px 16px;
  font-weight: 600;
  width: 100%;
  cursor: pointer;
}
.btn-primary:hover { background: var(--primary-hover); }
.card {
  background: var(--surface);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}
.kpi { padding: 16px; }
.kpi .label { color: var(--muted); font-size: 13px; }
.kpi .value { font-size: 22px; font-weight: 700; margin-top: 6px; }
"""

    _LOGIN = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Login · POS</title>
  <link rel="stylesheet" href="./pos.css" />
  <style>
    .login-wrap {
      min-height: 100vh; display: grid; place-items: center; padding: 24px;
      background: radial-gradient(circle at top, #ffe9ec, var(--bg) 55%);
    }
    .login-card { width: 100%; max-width: 380px; padding: 28px; }
    .brand { text-align: center; margin-bottom: 18px; }
    .brand .logo {
      width: 48px; height: 48px; margin: 0 auto 8px; border-radius: 12px;
      background: var(--primary); color: #fff; display: grid; place-items: center;
      font-weight: 800; font-size: 22px;
    }
    .brand h1 { font-size: 20px; margin: 0 0 6px; }
    .brand p { margin: 0; color: var(--muted); font-size: 13px; line-height: 1.4; }
    label { display: block; font-size: 12px; color: var(--muted); margin: 14px 0 6px; }
    input[type=text], input[type=password] {
      width: 100%; padding: 12px; border-radius: 10px; border: 1px solid var(--border);
    }
    .row { display: flex; align-items: center; gap: 8px; margin: 14px 0 18px; font-size: 13px; }
    .footer {
      display: flex; justify-content: space-between; margin-top: 16px;
      color: var(--muted); font-size: 12px;
    }
    .ok-dot { color: var(--ok); }
  </style>
</head>
<body>
  <div class="login-wrap">
    <form class="card login-card" onsubmit="return false;">
      <div class="brand">
        <div class="logo">P</div>
        <h1>Bienvenido de vuelta</h1>
        <p>Punto de venta y gestión. La operación puede seguir incluso sin Internet.</p>
      </div>
      <label>USUARIO</label>
      <input type="text" placeholder="usuario@negocio.com" />
      <label>CONTRASEÑA</label>
      <input type="password" placeholder="••••••••" />
      <div class="row"><input type="checkbox" id="r" checked /><label for="r" style="margin:0">Recordarme</label></div>
      <button class="btn-primary" type="submit">Iniciar sesión</button>
      <div class="footer"><span class="ok-dot">● Terminal verificado</span><span>v1.0</span></div>
    </form>
  </div>
</body>
</html>
"""

    _SHELL = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Shell · POS</title>
  <link rel="stylesheet" href="./pos.css" />
  <style>
    .app { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }
    .sidebar { background: var(--surface); border-right: 1px solid var(--border); padding: 16px 12px; }
    .sidebar .section { color: var(--muted); font-size: 11px; margin: 16px 8px 6px; letter-spacing: .04em; }
    .sidebar a {
      display: block; padding: 10px 12px; border-radius: 8px; color: var(--text);
      text-decoration: none; font-size: 14px;
    }
    .sidebar a.active, .sidebar a:hover { background: #ffe9ec; color: var(--primary); }
    .main { display: flex; flex-direction: column; }
    .topbar {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 16px; background: #fff7ed; border-bottom: 1px solid #fed7aa; font-size: 13px;
    }
    .content { padding: 20px; }
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <strong style="padding:8px">POS · Plan</strong>
      <div class="section">OPERACIÓN</div>
      <a class="active" href="#">Dashboard</a>
      <a href="#">POS</a>
      <a href="#">Delivery</a>
      <a href="#">Caja</a>
      <div class="section">CATÁLOGO</div>
      <a href="#">Productos</a>
      <a href="#">Clientes</a>
      <div class="section">GESTIÓN</div>
      <a href="#">Historial</a>
      <a href="#">Reportes</a>
      <a href="#">Anulaciones</a>
    </aside>
    <div class="main">
      <div class="topbar">
        <span>Tu licencia vence pronto. Sigue operando sin interrupciones.</span>
        <span style="color:var(--ok)">● En línea</span>
      </div>
      <main class="content">
        <!-- outlet: dashboard / pos / ... -->
        <p>Contenido de la vista activa</p>
      </main>
    </div>
  </div>
</body>
</html>
"""

    _DASHBOARD = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <title>Dashboard · POS</title>
  <link rel="stylesheet" href="./pos.css" />
  <style>
    .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 10px 8px; border-bottom: 1px solid var(--border); text-align: left; }
    th { color: var(--muted); font-weight: 600; }
  </style>
</head>
<body style="padding:20px">
  <h2>Dashboard</h2>
  <div class="grid">
    <div class="card kpi"><div class="label">Ventas</div><div class="value">S/ 0.00</div></div>
    <div class="card kpi"><div class="label">Ticket promedio</div><div class="value">S/ 0.00</div></div>
    <div class="card kpi"><div class="label">Descuentos</div><div class="value">S/ 0.00</div></div>
    <div class="card kpi"><div class="label">Anulado</div><div class="value">S/ 0.00</div></div>
  </div>
  <div class="card" style="margin-top:16px; padding:12px">
    <strong>Ventas del período</strong>
    <table>
      <thead><tr><th>Fecha</th><th>Venta</th><th>Tipo</th><th>Medio</th><th>Total</th></tr></thead>
      <tbody><tr><td colspan="5" style="color:var(--muted)">Sin operaciones</td></tr></tbody>
    </table>
  </div>
</body>
</html>
"""
