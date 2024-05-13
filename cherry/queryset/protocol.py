from typing import Any, Optional, Protocol


class QuerySetProtocol(Protocol):
    async def first(self) -> Optional[Any]:
        ...

    async def get(self) -> Optional[Any]:
        ...

    async def all(self) -> list[Any]:
        ...

    async def random_one(self) -> Optional[Any]:
        ...

    async def paginate(self) -> list[Any]:
        ...
