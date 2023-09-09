from typing import TypeVar

from sqlalchemy import Column

T = TypeVar("T")


def cast_column(arg: T) -> Column[T]:
    """make sure the argument is a Column"""
    if not isinstance(arg, Column):
        raise TypeError(f"{arg} is not a Column")
    return arg


__all__ = [
    "cast_column",
]
