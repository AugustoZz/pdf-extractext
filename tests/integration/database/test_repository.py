import pytest
import pytest_asyncio
from app.infrastructure.database.repository import DocumentRepository
from app.infrastructure.database.connection import connect_to_mongo, close_mongo_connection, get_database

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Conecta a la base de datos de test antes de correr las pruebas."""
    await connect_to_mongo()
    db = get_database()
    # Limpiamos la colección antes de correr las pruebas
    await db["documents"].delete_many({})
    yield
    # Limpiamos la colección después y cerramos conexión
    await db["documents"].delete_many({})
    await close_mongo_connection()

@pytest.mark.asyncio
async def test_repository_crud():
    # 1. Create
    data = {
        "text": "Contenido de prueba",
        "checksum": "abc123hash456",
        "page_count": 5,
        "metadata": {"author": "Test Author"}
    }
    
    created_doc = await DocumentRepository.create(data)
    assert created_doc is not None
    assert "id" in created_doc
    assert created_doc["text"] == "Contenido de prueba"
    
    doc_id = created_doc["id"]
    
    # 2. Get by ID
    fetched_doc = await DocumentRepository.get_by_id(doc_id)
    assert fetched_doc is not None
    assert fetched_doc["id"] == doc_id
    assert fetched_doc["checksum"] == "abc123hash456"
    
    # 3. Get by Checksum
    checksum_doc = await DocumentRepository.get_by_checksum("abc123hash456")
    assert checksum_doc is not None
    assert checksum_doc["id"] == doc_id
    
    # 4. Update
    update_data = {"page_count": 10, "text": "Texto actualizado"}
    updated_doc = await DocumentRepository.update(doc_id, update_data)
    assert updated_doc is not None
    assert updated_doc["page_count"] == 10
    assert updated_doc["text"] == "Texto actualizado"
    assert updated_doc["checksum"] == "abc123hash456" # Should not change
    
    # 5. Get All
    all_docs = await DocumentRepository.get_all()
    assert len(all_docs) == 1
    assert all_docs[0]["id"] == doc_id
    
    # 6. Delete
    delete_result = await DocumentRepository.delete(doc_id)
    assert delete_result is True
    
    # Ensure deleted
    deleted_doc = await DocumentRepository.get_by_id(doc_id)
    assert deleted_doc is None

@pytest.mark.asyncio
async def test_get_by_checksum_not_found():
    doc = await DocumentRepository.get_by_checksum("invalid_checksum")
    assert doc is None
