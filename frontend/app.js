const API_URL = '/api/v1';

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const sections = document.querySelectorAll('.content-section');
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
const uploadProcessing = document.getElementById('upload-processing');
const uploadResult = document.getElementById('upload-result');

// Modal Elements
const docModal = document.getElementById('doc-modal');
const modalFilename = document.getElementById('modal-filename');
const modalChecksum = document.getElementById('modal-checksum');
const modalText = document.getElementById('modal-text');
const btnSaveDoc = document.getElementById('btn-save-doc');
const btnDeleteDoc = document.getElementById('btn-delete-doc');

let currentDocId = null;

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    setupNavigation();
    setupDragAndDrop();
    loadDocuments();
});

// Navigation
function setupNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            // Update active nav
            navItems.forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');

            // Show target section
            const targetId = item.getAttribute('data-target');
            sections.forEach(sec => sec.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');

            if (targetId === 'documents-section') {
                loadDocuments();
            }
        });
    });
}

function goToDocuments() {
    document.querySelector('[data-target="documents-section"]').click();
}

// Drag and Drop
function setupDragAndDrop() {
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', function() {
        handleFiles(this.files);
    });
}

function handleFiles(files) {
    if (files.length === 0) return;
    const file = files[0];
    
    if (file.type !== 'application/pdf') {
        showToast('Por favor, selecciona un archivo PDF válido.', 'error');
        return;
    }
    
    // Check size (10MB)
    if (file.size > 10 * 1024 * 1024) {
        showToast('El archivo supera el límite de 10MB.', 'error');
        return;
    }

    uploadFile(file);
}

// API Interactions
async function uploadFile(file) {
    dropZone.classList.add('hidden');
    uploadProcessing.classList.remove('hidden');
    uploadResult.classList.add('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_URL}/extract`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Error al procesar el documento');
        }

        showUploadResult(data);
        showToast('Documento procesado correctamente', 'success');
        
    } catch (error) {
        resetUpload();
        showToast(error.message, 'error');
    }
}

function showUploadResult(data) {
    uploadProcessing.classList.add('hidden');
    uploadResult.classList.remove('hidden');

    document.getElementById('res-pages').textContent = `${data.page_count} páginas`;
    document.getElementById('res-filename').textContent = data.filename;
    document.getElementById('res-checksum').textContent = data.checksum;
    document.getElementById('res-text').textContent = data.text || 'Sin texto extraíble';
}

function resetUpload() {
    fileInput.value = '';
    dropZone.classList.remove('hidden');
    uploadProcessing.classList.add('hidden');
    uploadResult.classList.add('hidden');
}

// Documents CRUD
async function loadDocuments() {
    const tbody = document.getElementById('documents-tbody');
    const loadingState = document.getElementById('docs-loading');
    const emptyState = document.getElementById('docs-empty');

    tbody.innerHTML = '';
    loadingState.classList.remove('hidden');
    emptyState.classList.add('hidden');

    try {
        const response = await fetch(`${API_URL}/documents`);
        const result = await response.json();
        const docs = result.data || [];

        loadingState.classList.add('hidden');

        if (docs.length === 0) {
            emptyState.classList.remove('hidden');
            return;
        }

        docs.forEach(doc => {
            const tr = document.createElement('tr');
            const date = new Date(doc.created_at).toLocaleDateString('es-ES', {
                year: 'numeric', month: 'short', day: 'numeric',
                hour: '2-digit', minute:'2-digit'
            });
            
            // Handle different ID formats (MongoDB uses _id as ObjectId string usually, but pydantic parses it to id or _id depending on config)
            const docId = doc.id || doc._id;

            tr.innerHTML = `
                <td>
                    <div style="display:flex; align-items:center; gap:8px;">
                        <i class="ph-fill ph-file-pdf" style="color:var(--danger)"></i>
                        ${doc.filename}
                    </div>
                </td>
                <td>${doc.page_count}</td>
                <td style="color:var(--text-secondary)">${date}</td>
                <td>
                    <button class="icon-btn" onclick="openDocument('${docId}')" title="Ver/Editar">
                        <i class="ph ph-pencil-simple"></i>
                    </button>
                    <button class="icon-btn" onclick="deleteDocumentFromTable('${docId}')" title="Eliminar">
                        <i class="ph ph-trash" style="color:var(--danger)"></i>
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

    } catch (error) {
        loadingState.classList.add('hidden');
        showToast('Error al cargar documentos', 'error');
    }
}

async function openDocument(id) {
    try {
        const response = await fetch(`${API_URL}/documents/${id}`);
        if (!response.ok) throw new Error('No se pudo cargar el documento');
        
        const doc = await response.json();
        currentDocId = doc.id || doc._id;
        
        modalFilename.value = doc.filename;
        modalChecksum.value = doc.checksum;
        modalText.value = doc.text;
        
        docModal.classList.remove('hidden');
    } catch (error) {
        showToast(error.message, 'error');
    }
}

function closeModal() {
    docModal.classList.add('hidden');
    currentDocId = null;
}

btnSaveDoc.addEventListener('click', async () => {
    if (!currentDocId) return;
    
    try {
        const response = await fetch(`${API_URL}/documents/${currentDocId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                filename: modalFilename.value,
                text: modalText.value
            })
        });

        if (!response.ok) throw new Error('Error al actualizar');
        
        showToast('Documento actualizado correctamente', 'success');
        closeModal();
        loadDocuments();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

btnDeleteDoc.addEventListener('click', async () => {
    if (!currentDocId) return;
    if (confirm('¿Estás seguro de que deseas eliminar este documento permanentemente?')) {
        await deleteDocument(currentDocId);
        closeModal();
    }
});

async function deleteDocumentFromTable(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este documento permanentemente?')) {
        await deleteDocument(id);
    }
}

async function deleteDocument(id) {
    try {
        const response = await fetch(`${API_URL}/documents/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Error al eliminar');
        
        showToast('Documento eliminado', 'success');
        loadDocuments();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Utilities
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'ph-check-circle' : 
                 type === 'error' ? 'ph-warning-circle' : 'ph-info';
                 
    toast.innerHTML = `
        <i class="ph-fill ${icon}" style="font-size:24px"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s forwards';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
