import asyncio
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING, Union

from sqlalchemy import Engine, event, make_url, MetaData, URL
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

if TYPE_CHECKING:
    from cherry.models import Model

DictStrAny = Dict[str, Any]
Values = Union[DictStrAny, List[DictStrAny]]


class Database:
    _engine: AsyncEngine
    _metadata: MetaData
    _models: Dict[str, Type["Model"]] = {}
    _url: URL
    _connect: Optional[AsyncConnection] = None
    _lock: asyncio.Lock = asyncio.Lock()
    _counter: int = 0

    def __init__(self, url: Union[str, URL], echo: bool = False) -> None:
        if isinstance(url, str):
            url = make_url(url)
        self._engine = create_async_engine(url, echo=echo)
        self._metadata = MetaData()
        self._url = url

    @property
    def metadata(self):
        return self._metadata

    @property
    def engine(self):
        return self._engine

    async def create_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def drop_all(self):
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)

    async def init(self):
        self.init_all_model()

        if self._url.drivername.startswith("sqlite"):
            self._set_sqlite()

        await self.create_all()

    def init_all_model(self):
        for model in self._models.values():
            model._generate_sqlalchemy_column()
            model._generate_sqlalchemy_table(self._metadata)

    async def dispose(self):
        await self._engine.dispose()

    def add_model(self, model: Type["Model"]):
        self._models[model.__meta__.tablename] = model
        model.__meta__.database = self

    async def __aenter__(self) -> AsyncConnection:
        async with self._lock:
            if self._connect is None:
                self._connect = self._engine.connect()
            self._counter += 1
            if self._counter == 1:
                await self._connect.start()
            return self._connect

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._lock:
            self._counter -= 1
            if self._counter == 0 and self._connect is not None:
                if exc_type is not None:
                    await self._connect.rollback()
                else:
                    await self._connect.commit()
                await self._connect.close()
                self._connect = None

    def _set_sqlite(self):
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listens_for(Engine, "connect")(set_sqlite_pragma)
