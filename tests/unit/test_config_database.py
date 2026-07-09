"""
Tests para config.database
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.config import database


def _async_context_manager(return_value=None, side_effect=None):
    """Build a mock usable as `async with cm:` for engine.begin()."""
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=return_value, side_effect=side_effect)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.mark.asyncio
async def test_init_db_success():
    with patch.object(type(database.engine), "begin", return_value=_async_context_manager()):
        await database.init_db()  # should not raise


@pytest.mark.asyncio
async def test_init_db_reraises_on_failure():
    failing_cm = _async_context_manager(side_effect=RuntimeError("db unreachable"))
    with patch.object(type(database.engine), "begin", return_value=failing_cm):
        with pytest.raises(RuntimeError, match="db unreachable"):
            await database.init_db()


@pytest.mark.asyncio
async def test_get_db_yields_and_closes_session():
    gen = database.get_db()

    session = await gen.__anext__()
    assert isinstance(session, database.AsyncSession)

    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
