import http from 'k6/http';
import { Trend } from 'k6/metrics';
import { check } from 'k6';

const statusTrend = new Trend('status_codes');

export const options = {
    stages: [
        { duration: '10s', target: 100 },
        { duration: '20s', target: 100 },
        { duration: '10s', target: 0 },
    ],
};

const BASE_URL = 'http://extractor-lb';

// Carga de PDFs en modo binario durante la inicializaciÃ³n (init context de k6)
const pdfFiles = [
    open('/stress/pdfs/2020-Scrum-Guide-Spanish-Latin-South-American.pdf', 'b'),
    open('/stress/pdfs/Essential-Kanban-Condensed-Spanish.pdf', 'b'),
    open('/stress/pdfs/Filosofia Lean.pdf', 'b'),
    open('/stress/pdfs/scrum_manager_historias_usuario.pdf', 'b'),
];

export default function () {
    // SelecciÃ³n aleatoria de un PDF de la lista
    const randomPdf = pdfFiles[Math.floor(Math.random() * pdfFiles.length)];

    const params = {
        headers: {
            'Content-Type': 'application/pdf',
        },
    };

    const res = http.post(`${BASE_URL}/extract`, randomPdf, params);

    statusTrend.add(res.status);

    check(res, {
        'status 200': (r) => r.status === 200,
    });
}



