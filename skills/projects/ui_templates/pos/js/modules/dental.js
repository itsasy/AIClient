import { Registry } from "../registry.js";
import { request, json } from "../api.js";
import { renderPatients } from "../views/patients.js";
import { renderPatientHub } from "../views/patient-hub.js";

const dentalApi = {
  agenda: {
    list: (patient_id) => request(`/api/agenda?patient_id=${patient_id}`),
    create: (item) => request("/api/agenda", json("POST", item)),
    status: (id, status) => request(`/api/agenda/${id}/status`, json("POST", { status })),
  },
  patients: {
    list: () => request("/api/patients"),
    get: (id) => request(`/api/patients/${id}`),
    create: (item) => request("/api/patients", json("POST", item)),
  },
  clinicalHistory: {
    list: (patient_id) => request(`/api/patients/${patient_id}/history`),
    add: (patient_id, content) => request(`/api/patients/${patient_id}/history`, json("POST", { content })),
  },
  odontogram: {
    get: (patient_id) => request(`/api/odontogram/${patient_id}`),
    finding: (patient_id, finding) => request(`/api/odontogram/${patient_id}/finding`, json("POST", finding)),
  },
  prescriptions: { list: () => request("/api/prescriptions"), create: (item) => request("/api/prescriptions", json("POST", item)) }
};

Registry.register({
  id: 'dental',
  api: dentalApi,
  menu: { title: 'ODONTOLOGIA', items: [
    { view: 'patients', label: 'Pacientes & Ficha Clínica' }
  ]},
  routes: {
    'patients': (outlet) => renderPatients(outlet, () => Registry.routes['patients'](outlet)),
    'patient-hub': (outlet) => renderPatientHub(outlet)
  }
});
