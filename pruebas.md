La landing está **aceptable** para smoke G: HTML completo, hero, ≥3 secciones, CTA, footer, Tailwind. Calidad “marketing simple”, no premium; el pipeline cumple.

`/plan` **técnicamente** ya no crashea, pero aún:

- habilita tools `file` (no ideal para planning),
- el coder recibe **confirmación** (134 chars) y eso se materializa como “plan”.

Eso es deuda de calidad del plan; no impide seguir con scaffolds/API.

---

## Batería de comandos `ai` (objetivos del proyecto)

Ejecutá desde `~/Workspace/AIClient` con `TARGET_PROJECT_ROOT` apuntando al demo (p.ej. `pos-demo`).  
Anotá PASS/FAIL. Si algo falla, solo el tramo desde `Engine procesando` hasta el error.

### 0. Sanity del motor
```bash
ai "hola"
ai "¿qué puedes hacer?"
```

### 1. Análisis del **producto** (TARGET)
```bash
ai "analiza el proyecto"
ai "/review arquitectura módulos POS"
```

### 2. Locale + Standards + Spec/Plan (SDD)
```bash
ai "/spec POS restaurante multiestación offline país=AR"
ai "/plan POS restaurante país=AR"
ai "/spec e-commerce carrito checkout país=AR"
```
Comprobar: logs `Locale AR` / `sources=obsidian`; Standards con chars altos.  
Abrir el `.specs/*.md` generado: debe ser **documento**, no una frase “se ha creado…”.

### 3. Stack POS (scaffold)
```bash
ai "/build pos-stack país=AR"
ai "/build ui-shell"
# si no pisa nada:
ai "/build ui-shell --force"
```

### 4. Enrich + facade (contratos)
```bash
ai "/build enrich catalog país=AR"
ai "/build enrich cash país=AR"
ai "/build enrich pos país=AR"
```
Luego smoke Python (no `ai`):
```bash
cd /tmp
PYTHONPATH=/home/alexis/Workspace/pos-demo python3 -c "
from src.modules.pos.sale_facade import SaleFacade
s = SaleFacade(locale='AR')
s.seed_product('SKU1','Café',15.0)
r = s.sell([('SKU1',2)])
print(r.get('ok'), r.get('total'), r.get('payment',{}).get('status'), r.get('estado'))
"
```

### 5. Vertical restaurante
```bash
ai "/build restaurant-stack país=AR"   # si el alias existe; si no:
ai "/build enrich dashboard país=AR"
```
Smoke:
```bash
PYTHONPATH=/home/alexis/Workspace/pos-demo python3 -c "
from src.modules.restaurant.dashboard_facade import DashboardFacade
print(DashboardFacade(locale='AR').snapshot())
"
```

### 6. Vertical clínica / dental (si sigue en el demo)
```bash
ai "/build dental-stack país=AR"
```
Smoke:
```bash
PYTHONPATH=/home/alexis/Workspace/pos-demo python3 -c "
from src.modules.clinical.session_facade import ClinicalSessionFacade
print(ClinicalSessionFacade(locale='AR').run_demo_session().get('ok'))
"
```

### 7. API del producto (con servidor levantado en pos-demo)
```bash
curl -s http://127.0.0.1:8765/api/health
curl -s http://127.0.0.1:8765/api/catalog
curl -s -X POST http://127.0.0.1:8765/api/sell \
  -H 'Content-Type: application/json' \
  -d '{"items":[["SKU1",1]],"method":"efectivo"}'
curl -s http://127.0.0.1:8765/api/sales/history
curl -s http://127.0.0.1:8765/api/reports/summary
```

### 8. Landings / file_creation
```bash
ai "Crea landing_vinoteca.html con Tailwind para vinoteca artesanal"
ai "Crea landing_ecommerce.html con Tailwind para tienda de café con carrito visual"
```
Comprobar:
```bash
ROOT=$(python3 -c 'from core.config import Config; print(Config.TARGET_PROJECT_ROOT)')
wc -c "$ROOT"/landing_*.html
tail -5 "$ROOT"/landing_vinoteca.html   # debe cerrar </html>
```

### 9. E-commerce (alcance actual = spec/plan + landing; no stack completo)
```bash
ai "/spec e-commerce catálogo carrito checkout pagos país=AR"
ai "/plan e-commerce checkout país=AR"
ai "Crea landing_shop.html con Tailwind: hero, grid de productos, CTA carrito"
```
Un e-commerce **backend completo** (órdenes, stock, pasarela real) **aún no** es objetivo cerrado; lo razonable es spec + UI landing/shell alineada a Standards.

### 10. Multi-locale (sin inventar fisco)
```bash
ai "/spec POS país=MX"
ai "/build payments país=MX"
ai "/spec POS país=ES"
```

### 11. No-regresión paths / write
```bash
ai "Crea notas_smoke.md con un título y tres bullets de prueba"
# archivo bajo TARGET, no en / de AIClient
```

---

## Qué cuenta como “objetivo cumplido”

| Objetivo | Comandos clave | Criterio PASS |
|----------|----------------|---------------|
| Orquestador estable | 0 | Sin traceback |
| Análisis TARGET | 1 | Habla de pos-demo / modules |
| SDD locale + standards | 2 | AR + standards; plan **con contenido** |
| POS generable | 3–4–7 | Stack + SaleFacade + API sell |
| Restaurante | 5 | DashboardFacade / stack |
| Clínica | 6 | session demo ok |
| Landings | 8 | HTML completo en TARGET |
| E-commerce (fase actual) | 9 | Spec/plan + landing shop |
| Multi-país | 10 | Spec/adapters sin hardcode PE |

---

## Orden sugerido hoy

1. §0 + §1  
2. §3 + §4 + §7 (núcleo POS)  
3. §8 landings  
4. §5 / §6 verticales  
5. §2 y §9 mirando **calidad del `.md`**, no solo `ok: True`

Si `/plan` sigue guardando solo “Se ha creado el archivo…”, el siguiente arreglo es: **no tools en intent=planning** + coder que no acepte confirmación como contenido del plan. Podés seguir testeando C/D/E/G mientras tanto.