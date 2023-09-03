from enum import auto, Enum
from typing import Optional, TypeVar
from typing_extensions import Annotated


class FieldInfoEnum(Enum):
    primary_key = auto()
    autoincrement = auto()
    index = auto()
    unique = auto()


T = TypeVar("T")

PrimaryKey = Annotated[T, FieldInfoEnum.primary_key]
AutoIncrement = Annotated[T, FieldInfoEnum.autoincrement]
AutoIncrementPrimaryKey = Annotated[
    T,
    FieldInfoEnum.primary_key,
    FieldInfoEnum.autoincrement,
]
AutoIncrementIntPrimaryKey = Annotated[
    Optional[int],
    FieldInfoEnum.primary_key,
    FieldInfoEnum.autoincrement,
]

Index = Annotated[T, FieldInfoEnum.index]
Unique = Annotated[T, FieldInfoEnum.unique]
