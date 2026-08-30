// Enfoque API (Opción A): Los módulos extienden el objeto global 'api' exportado por api.js.
// Esto permite que las vistas importen { api } directamente y usen los endpoints inyectados.
import { api } from "./api.js";  export const Registry = {   routes: {},   menus: [],      register(mod) {     if (mod.routes) {       Object.assign(this.routes, mod.routes);     }     if (mod.menu) {       this.menus.push(mod.menu);     }     if (mod.api) {       Object.assign(api, mod.api);     }   } };
