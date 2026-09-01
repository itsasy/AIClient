
import { Registry } from "../registry.js";
import { request } from "../api.js";
import { renderReportes } from "../views/reportes.js";

Registry.register({
  id: 'reports',
  api: { reports: { summary: () => request("/api/reports/summary") } },
  menu: { title: 'GESTION', items: [
    { view: 'reportes', label: 'Reportes' }
  ]},
  routes: {
    'reportes': (outlet) => renderReportes(outlet, () => Registry.routes['reportes'](outlet))
  }
});
