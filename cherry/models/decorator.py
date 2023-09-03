from functools import wraps
from typing import Type, TYPE_CHECKING, TypeVar
from typing_extensions import ParamSpec

if TYPE_CHECKING:
    from .models import Model

P = ParamSpec("P")
R = TypeVar("R")


def check_connected(f):
    @wraps(f)
    def inner(
        cls_or_self: Type["Model"] | "Model",
        *args,
        **kwargs,
    ):
        if cls_or_self.__meta__.abstract:
            raise ValueError("Cannot instantiate abstract model")
        if not hasattr(cls_or_self.__meta__, "database"):
            raise ValueError(
                f"{cls_or_self.__meta__.tablename} has no been bound to any database",
            )
        return f(cls_or_self, *args, **kwargs)

    return inner
