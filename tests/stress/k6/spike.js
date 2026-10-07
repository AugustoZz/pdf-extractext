// Prueba spike (modelo cerrado) con el perfil de la cátedra:
// 0 → 100 VUs en 10 s, 20 s sostenidos y bajada a 0 en 10 s.
// Igual que el script del profesor: PDF crudo en el body y elegido al azar.
import http from 'k6/http';
import { check } from 'k6';

const TARGET_URL = __ENV.TARGET_URL || 'http://extractor-lb/extract';

// open() sólo funciona en la etapa de inicialización: los PDFs se cargan una vez por VU.
const pdfs = [
  '2020-Scrum-Guide-Spanish-Latin-South-American.pdf',
  'Essential-Kanban-Condensed-Spanish.pdf',
  'Filosofia Lean.pdf',
  'scrum_manager_historias_usuario.pdf',
].map((name) => open(`/stress/pdfs/${name}`, 'b'));

export const options = {
  stages: [
    { duration: '10s', target: 100 },
    { duration: '20s', target: 100 },
    { duration: '10s', target: 0 },
  ],
};

export default function () {
  const pdf = pdfs[Math.floor(Math.random() * pdfs.length)];
  const res = http.post(TARGET_URL, pdf, {
    headers: { 'Content-Type': 'application/pdf' },
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}
