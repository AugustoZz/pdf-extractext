import pytest
import pytest_asyncio
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.infrastructure.database.repository import DocumentRepository
from app.infrastructure.database.connection import connect_to_mongo, close_mongo_connection, get_database

@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """
    Conecta a la base de datos de TEST antes de correr las pruebas.

    Esta suite hace ``delete_many({})`` sobre la colección, así que jamás debe
    apuntar a la base de desarrollo: se conecta explícitamente a
    ``MONGODB_TEST_DB_NAME`` y verifica que sea distinta de la base real.
    """
    assert settings.MONGODB_TEST_DB_NAME != settings.MONGODB_DB_NAME, (
        "MONGODB_TEST_DB_NAME no puede ser igual a MONGODB_DB_NAME: "
        "los tests borran la colección y destruirían los datos de desarrollo."
    )

    await connect_to_mongo(db_name=settings.MONGODB_TEST_DB_NAME)
    db = get_database()
    assert db.name == settings.MONGODB_TEST_DB_NAME

    # Mismos índices que en producción, para que los tests validen el esquema real
    await DocumentRepository.ensure_indexes()

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


@pytest.mark.asyncio
async def test_duplicate_checksum_is_rejected_by_unique_index():
    """El índice único impide insertar dos documentos con el mismo checksum."""
    data = {"text": "Original", "checksum": "checksum-repetido", "page_count": 1}
    await DocumentRepository.create(data)

    with pytest.raises(DuplicateKeyError):
        await DocumentRepository.create(
            {"text": "Copia", "checksum": "checksum-repetido", "page_count": 1}
        )


@pytest.mark.asyncio
async def test_update_with_empty_data_returns_document_unchanged():
    """Un update sin campos no debe romper: Mongo rechaza un '$set' vacío."""
    created = await DocumentRepository.create(
        {"text": "Sin cambios", "checksum": "checksum-vacio", "page_count": 2}
    )

    result = await DocumentRepository.update(created["id"], {})

    assert result is not None
    assert result["text"] == "Sin cambios"
    assert result["page_count"] == 2


@pytest.mark.asyncio
async def test_update_ignores_immutable_fields():
    """El checksum no puede reescribirse desde un update."""
    created = await DocumentRepository.create(
        {"text": "Contenido", "checksum": "checksum-inmutable", "page_count": 1}
    )

    updated = await DocumentRepository.update(
        created["id"], {"checksum": "hackeado", "text": "Contenido editado"}
    )

    assert updated["checksum"] == "checksum-inmutable"
    assert updated["text"] == "Contenido editado"


@pytest.mark.asyncio
async def test_update_does_not_mutate_caller_dict():
    """El repositorio no debe modificar el diccionario que recibe."""
    created = await DocumentRepository.create(
        {"text": "Base", "checksum": "checksum-no-mutar", "page_count": 1}
    )
    payload = {"checksum": "otro", "text": "Nuevo"}

    await DocumentRepository.update(created["id"], payload)

    assert payload == {"checksum": "otro", "text": "Nuevo"}


@pytest.mark.asyncio
async def test_update_nonexistent_document_returns_none():
    doc = await DocumentRepository.update("507f1f77bcf86cd799439011", {"text": "x"})
    assert doc is None
