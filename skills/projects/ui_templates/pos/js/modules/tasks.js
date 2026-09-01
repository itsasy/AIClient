
import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderTasks } from "../views/tasks.js";

Registry.register({
  id: 'tasks',
  api: {
    tasks: { list: () => request("/api/tasks"), create: (item) => request("/api/tasks", json("POST", item)), status: (id, status) => request(`/api/tasks/${id}/status`, json("POST", { status })) }
  },
  menu: { title: 'GESTION', items: [
    { view: 'tasks', label: 'Tareas' }
  ]},
  routes: {
    'tasks': (outlet) => renderTasks(outlet, () => Registry.routes['tasks'](outlet))
  }
});
