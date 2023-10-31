import asyncio
from typing import Any, Dict, Optional, Type, TYPE_CHECKING, Union

from sqlalchemy import Engine, event, make_url, MetaData, URL
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    create_async_engine,
)

if TYPE_CHECKING:
    from cherry.models import Model

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Database:
    _engine: AsyncEngine
    _metadata: MetaData
    _models: Dict[str, Type["Model"]] = {}
    _url: URL
    _connect: Optional[AsyncConnection] = None
    _lock: asyncio.Lock = asyncio.Lock()
    _counter: int = 0

    def __init__(self, url: Union[str, URL], **kwargs: Any) -> None:
        if isinstance(url, str):
            url = make_url(url)
        self._engine = create_async_engine(url=url, **kwargs)
        self._metadata = MetaData(naming_convention=NAMING_CONVENTION)
        self._url = url

    @property
    def metadata(self) -> MetaData:
        return self._metadata

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def create_all(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.create_all)

    async def drop_all(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(self._metadata.drop_all)

    async def init(self, set_sqlite_pragma: bool = True) -> None:
        self.init_all_model()

        if set_sqlite_pragma and self._url.drivername.startswith("sqlite"):
            self._set_sqlite()

        await self.create_all()

    def init_all_model(self) -> None:
        for model in self._models.values():
            model._generate_sqlalchemy_column()
            model._generate_sqlalchemy_table(self._metadata)

    async def dispose(self) -> None:
        await self._engine.dispose()

    def add_model(self, model: Type["Model"]) -> None:
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

    def _set_sqlite(self) -> None:
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        event.listens_for(Engine, "connect")(set_sqlite_pragma)
