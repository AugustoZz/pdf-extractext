"""El arranque no debe aceptar documentos sin índice único de checksum."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pymongo.errors import OperationFailure

from app.infrastructure.database.repository import DocumentRepository
from app.main import app, lifespan


@pytest.mark.asyncio
async def test_checksum_index_failure_aborts_startup():
    collection = MagicMock()
    collection.create_index = AsyncMock(side_effect=OperationFailure("duplicates"))
    with patch.object(DocumentRepository, "_collection", return_value=collection):
        with pytest.raises(OperationFailure):
            await DocumentRepository.ensure_indexes()
    collection.create_index.assert_awaited_once_with("checksum", unique=True, name="uq_checksum")


@pytest.mark.asyncio
async def test_failed_startup_closes_database_and_client():
    with (
        patch("app.main.connect_to_mongo", new_callable=AsyncMock),
        patch("app.main.close_mongo_connection", new_callable=AsyncMock) as close,
        patch("app.main.DocumentRepository.ensure_indexes", new_callable=AsyncMock, side_effect=OperationFailure("duplicates")),
        patch("app.main.extractor_service") as service,
    ):
        service.start = AsyncMock()
        service.close = AsyncMock()
        with pytest.raises(OperationFailure):
            async with lifespan(app):
                pytest.fail("startup should have failed")
        close.assert_awaited_once()
        service.start.assert_not_awaited()
        service.close.assert_awaited_once()
