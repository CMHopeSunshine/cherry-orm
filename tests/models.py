from typing import Dict, List, Optional

import cherry
from tests.database import database

from pydantic import BaseModel


class User(cherry.Model):
    id: int | None = cherry.Field(default=None, primary_key=True, autoincrement=True)
    name: str = cherry.Field(unique=True, max_length=30)
    introduce: str = cherry.Field(long_text=True)
    age: int = 18
    money: float = 200

    class Meta:
        database = database


class Student(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    school: cherry.ForeignKey[Optional["School"]] = None

    class Meta:
        database = database


class School(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    students: cherry.ReverseRelation[List[Student]] = []

    class Meta:
        database = database


class Tag(cherry.Model):
    name: cherry.PrimaryKey[str]
    posts: cherry.ManyToMany[List["Post"]] = []

    class Meta:
        database = database


class Post(cherry.Model):
    id: cherry.AutoIntPK = None
    title: str
    tags: cherry.ManyToMany[List[Tag]] = []

    class Meta:
        database = database


class Data(BaseModel):
    a: str
    b: str


class JsonModel(cherry.Model):
    id: cherry.AutoIntPK = None
    data: Data
    lst: List[int]
    dic: Dict[str, Dict[str, str]]

    class Meta:
        database = database
