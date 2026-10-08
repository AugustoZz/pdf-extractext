const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');

const source = fs.readFileSync('frontend/app.js', 'utf8');
const document = {
    querySelectorAll: () => [],
    getElementById: () => ({addEventListener: () => {}}),
    addEventListener: () => {},
};
const context = vm.createContext({document, console, setTimeout});
vm.runInContext(source, context);
let accepted;
context.uploadFile = () => { accepted = true; };
context.showToast = () => {};
const cases = [
    ['PDF', 'application/pdf', 'file.pdf', 42, true],
    ['MIME vacío', '', 'file.PDF', 42, true],
    ['MIME genérico', 'application/octet-stream', 'file.pdf', 42, true],
    ['MIME binario', 'binary/octet-stream', 'file.pdf', 42, true],
    ['MIME incompatible', 'text/html', 'file.pdf', 42, false],
    ['Extensión inválida', 'application/pdf', 'file.exe', 42, false],
    ['Exceso de tamaño', 'application/pdf', 'file.pdf', 10485761, false],
];
for (const [name, type, filename, size, expected] of cases) {
    accepted = false;
    context.handleFiles([{type, name: filename, size}]);
    assert.equal(accepted, expected, name);
}
console.log(JSON.stringify({status: 'passed', checks: cases.map(entry => entry[0])}));
