from tests.database import database

import pytest_asyncio


@pytest_asyncio.fixture(autouse=True)
async def db():
    await database.drop_all()
    await database.create_all()
    yield
