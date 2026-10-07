// Prueba spike (modelo cerrado) con el perfil de la cátedra:
// 0 → 100 VUs en 10 s, 20 s sostenidos y bajada a 0 en 10 s.
// Igual que el script del profesor: PDF crudo en el body y elegido al azar.
import http from 'k6/http';
import { check } from 'k6';
import { open, SeekMode } from 'k6/experimental/fs';

const TARGET_URL = __ENV.TARGET_URL || 'http://extractor-lb/extract';

// Con open() de k6/fs cada PDF se carga una sola vez en memoria y lo comparten
// todos los VUs. El open() clásico guardaba una copia por VU: con 100 VUs, k6
// llegaba a ~4 GB y competía por RAM con las réplicas del extractor.
const pdfs = await Promise.all(
  [
    '2020-Scrum-Guide-Spanish-Latin-South-American.pdf',
    'Essential-Kanban-Condensed-Spanish.pdf',
    'Filosofia Lean.pdf',
    'scrum_manager_historias_usuario.pdf',
  ].map(async (name) => {
    const file = await open(`/stress/pdfs/${name}`);
    return { file, size: (await file.stat()).size };
  }),
);

export const options = {
  stages: [
    { duration: '10s', target: 100 },
    { duration: '20s', target: 100 },
    { duration: '10s', target: 0 },
  ],
};

// Copia el PDF a un buffer propio de la iteración, que se libera al terminarla.
async function readPdf({ file, size }) {
  const buffer = new Uint8Array(size);
  await file.seek(0, SeekMode.Start);
  let offset = 0;
  while (offset < size) {
    offset += await file.read(buffer.subarray(offset));
  }
  return buffer.buffer;
}

export default async function () {
  const body = await readPdf(pdfs[Math.floor(Math.random() * pdfs.length)]);
  const res = await http.asyncRequest('POST', TARGET_URL, body, {
    headers: { 'Content-Type': 'application/pdf' },
  });
  check(res, { 'status 200': (r) => r.status === 200 });
}
