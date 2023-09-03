from typing import Union

from sqlalchemy import MetaData, URL
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)


class Database:
    _engine: AsyncEngine
    _metadata: MetaData
    _session: async_sessionmaker[AsyncSession]

    def __init__(self, url: Union[str, URL], echo: bool = False) -> None:
        self._engine = create_async_engine(url, echo=echo)
        self._metadata = MetaData()
        self._session = async_sessionmaker(self._engine, expire_on_commit=False)

    async def create_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def drop_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)

    async def dispose(self):
        await self._engine.dispose()

    async def execute(
        self,
        *arg,
        **kwargs,
    ):
        async with self._engine.connect() as conn:
            result = await conn.execute(*arg, **kwargs)
            await conn.commit()
        return result
