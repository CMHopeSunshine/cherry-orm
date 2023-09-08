from typing import Dict, Type, TYPE_CHECKING, Union

from sqlalchemy import MetaData, URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
)

if TYPE_CHECKING:
    from cherry.models import Model


class Database:
    _engine: AsyncEngine
    _metadata: MetaData
    _models: Dict[str, Type["Model"]] = {}

    def __init__(self, url: Union[str, URL], echo: bool = False) -> None:
        self._engine = create_async_engine(url, echo=echo)
        self._metadata = MetaData()

    async def create_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def drop_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)

    async def init(self):
        for model in self._models.values():
            model._generate_sqlalchemy_column()
            model._generate_sqlalchemy_table(self._metadata)
        await self.create_all()

    async def dispose(self):
        await self._engine.dispose()

    def add_model(self, model: Type["Model"]):
        self._models[model.__meta__.tablename] = model
        model.__meta__.database = self

    async def execute(
        self,
        *arg,
        **kwargs,
    ):
        async with self._engine.connect() as conn:
            result = await conn.execute(*arg, **kwargs)
            await conn.commit()
        return result
