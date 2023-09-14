from typing import List, Optional

import cherry
from tests.database import database


class User(cherry.Model):
    id: int | None = cherry.Field(default=None, primary_key=True, autoincrement=True)
    name: str = cherry.Field(unique=True)
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
