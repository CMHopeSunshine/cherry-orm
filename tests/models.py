from __future__ import annotations

import cherry
from tests.database import database

from pydantic import BaseModel


class User(cherry.Model):
    id: int | None = cherry.Field(default=None, primary_key=True, autoincrement=True)
    name: str = cherry.Field(unique=True, max_length=30)
    introduce: str = cherry.Field(long_text=True)
    age: int = 18
    money: float = 200

    cherry_config = {"database": database}


class Student(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    school: School | None = cherry.Relationship(default=None, foreign_key=True)

    cherry_config = {"database": database}


class School(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    students: list[Student] = cherry.Relationship(
        default_factory=list,
        reverse_related=True,
    )

    cherry_config = {"database": database}


class Tag(cherry.Model):
    name: cherry.PrimaryKey[str]
    posts: list[Post] = cherry.Relationship(default_factory=list, many_to_many=True)

    cherry_config = {"database": database}


class Post(cherry.Model):
    id: cherry.AutoIntPK = None
    title: str
    tags: list[Tag] = cherry.Relationship(default_factory=list, many_to_many=True)

    cherry_config = {"database": database}


class Data(BaseModel):
    a: str
    b: str


class JsonModel(cherry.Model):
    id: cherry.AutoIntPK = None
    data: Data
    lst: list[int]
    dic: dict[str, dict[str, str]]

    cherry_config = {"database": database}
