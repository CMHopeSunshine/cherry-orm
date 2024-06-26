from typing import Any, Optional


class CompositeIndex:
    def __init__(
        self,
        *columns: str,
        name: Optional[str] = None,
        unique: bool = False,
        quote: Optional[bool] = None,
        info: Optional[dict[Any, Any]] = None,
    ) -> None:
        self.name = name
        self.columns = columns
        self.unique = unique
        self.quote = quote
        self.info = info
