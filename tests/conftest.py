from tests.database import database

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True, scope="function")
async def db():
    # await database.drop_all()
    await database.init()
    yield
    # await database.drop_all()
    await database.dispose()
