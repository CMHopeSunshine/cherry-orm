from typing import List, Optional

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class Student(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    school: Optional["School"] = cherry.Relationship(
        default=None,
        foreign_key="school_id",
        on_update="CASCADE",
        on_delete="CASCADE",
    )

    class Meta:
        database = db
        tablename = "student"


class School(cherry.Model):
    school_id: cherry.PrimaryKey[int]
    school_name: cherry.PrimaryKey[str]
    students: List[Student] = cherry.Relationship(default=[], reverse_related=True)

    class Meta:
        database = db
        tablename = "school"


class Tag(cherry.Model):
    tag_id1: cherry.PrimaryKey[int]
    tag_id2: cherry.PrimaryKey[int]
    content: str
    posts: List["Post"] = cherry.Relationship(
        default=[],
        many_to_many="post_id2",
        on_delete="RESTRICT",
        on_update="RESTRICT",
    )

    class Meta:
        database = db
        tablename = "tag"


class Post(cherry.Model):
    post_id1: cherry.PrimaryKey[int]
    post_id2: cherry.PrimaryKey[int]
    title: str
    tags: List[Tag] = cherry.Relationship(default=[], many_to_many="tag_id1")

    class Meta:
        database = db
        tablename = "post"
