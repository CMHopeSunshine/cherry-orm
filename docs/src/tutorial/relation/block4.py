from typing import Optional

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

    cherry_config = cherry.CherryConfig(tablename="student", database=db)


class School(cherry.Model):
    school_id: cherry.PrimaryKey[int]
    school_name: cherry.PrimaryKey[str]
    students: list[Student] = cherry.Relationship(default=[], reverse_related=True)

    cherry_config = cherry.CherryConfig(tablename="school", database=db)


class Tag(cherry.Model):
    tag_id1: cherry.PrimaryKey[int]
    tag_id2: cherry.PrimaryKey[int]
    content: str
    posts: list["Post"] = cherry.Relationship(
        default=[],
        many_to_many="post_id2",
        on_delete="RESTRICT",
        on_update="RESTRICT",
    )

    cherry_config = cherry.CherryConfig(tablename="tag", database=db)


class Post(cherry.Model):
    post_id1: cherry.PrimaryKey[int]
    post_id2: cherry.PrimaryKey[int]
    title: str
    tags: list[Tag] = cherry.Relationship(default=[], many_to_many="tag_id1")

    cherry_config = cherry.CherryConfig(tablename="post", database=db)
