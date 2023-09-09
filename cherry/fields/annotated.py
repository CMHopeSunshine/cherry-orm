from typing import Optional, TypeVar
from typing_extensions import Annotated

from .fields import Field, Relationship

T = TypeVar("T")

PrimaryKey = Annotated[T, Field(primary_key=True)]
"""Primary Key Field"""
AutoIncrement = Annotated[T, Field(autoincrement=True)]
"""Field with Auto Increment"""
AutoIncrementPK = Annotated[
    T,
    Field(primary_key=True, autoincrement=True),
]
"""Auto Increment Primary Key Field"""
AutoIntPK = Annotated[
    Optional[int],
    Field(primary_key=True, autoincrement=True),
]
"""Auto Increment Primary Key Integer Field"""

Index = Annotated[T, Field(index=True)]
"""Field with Index"""
Unique = Annotated[T, Field(unique=True)]
"""Field with Unique Constraint"""

ForeignKey = Annotated[T, Relationship(foreign_key=True)]
"""Foreign Key Relationship Field"""
ReverseRelated = Annotated[T, Relationship(reverse_related=True)]
"""Reverse Related Relationship Field"""
ManyToMany = Annotated[T, Relationship(many_to_many=True)]
"""Many To Many Relationship Field"""
