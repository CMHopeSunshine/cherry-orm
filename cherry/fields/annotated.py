from typing import Optional, TypeVar
from typing_extensions import Annotated

from .fields import Field, Relationship

T = TypeVar("T")

PrimaryKey = Annotated[T, Field(primary_key=True)]
AutoIncrement = Annotated[T, Field(autoincrement=True)]
AutoIncrementPrimaryKey = Annotated[
    T,
    Field(primary_key=True, autoincrement=True),
]
AutoIncrementIntPrimaryKey = Annotated[
    Optional[int],
    Field(primary_key=True, autoincrement=True),
]

Index = Annotated[T, Field(index=True)]
Unique = Annotated[T, Field(unique=True)]

ForeignKey = Annotated[T, Relationship(foreign_key=True)]
ReverseRelated = Annotated[T, Relationship(reverse_related=True)]
ManyToMany = Annotated[T, Relationship(many_to_many=True)]
