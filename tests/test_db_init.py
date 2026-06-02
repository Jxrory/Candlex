import pytest
import src.database as db


@pytest.mark.asyncio
async def test_async_session_maker_accessible_via_module():
    """Module attribute access tracks global reassignment inside get_engine()."""
    await db.get_engine()
    assert db.async_session_maker is not None
    assert callable(db.async_session_maker)


def test_main_imports_database_module():
    """main.py uses `import src.database as database` (the fix pattern).

    `from src.database import async_session_maker` creates a binding that
    does NOT track reassignment when get_engine() reassigns the module
    variable via `global`.  Module attribute access (database.X) does.
    """
    from src.main import database as main_db_ref
    assert main_db_ref is db
