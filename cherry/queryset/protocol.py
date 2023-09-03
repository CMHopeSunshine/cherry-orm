from typing import Any, List, Optional, Protocol


class QuerySetProtocol(Protocol):
    async def first(self) -> Optional[Any]:
        ...

    async def get(self) -> Optional[Any]:
        ...

    async def all(self) -> List[Any]:
        ...

    async def random_one(self) -> Optional[Any]:
        ...

    async def paginate(self) -> List[Any]:
        ...
