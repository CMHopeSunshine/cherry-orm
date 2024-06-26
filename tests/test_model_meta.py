from cherry.fields.fields import (
    BaseField,
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)
from cherry.fields.proxy import RelatedModelProxy
from cherry.fields.types import AutoString
from cherry.meta.config import CherryMeta
from tests.database import database
from tests.models import Post, School, Student, Tag, User

import pytest
import sqlalchemy.types as sa_types


@pytest.mark.asyncio
async def test_no_related():
    assert User.model_fields.keys() == {"id", "name", "introduce", "age", "money"}
    assert isinstance(User.__meta__, CherryMeta)
    assert User.__meta__.tablename == "User"
    assert User.__meta__.database == database
    assert User.__meta__.table is not None
    assert User.__meta__.metadata is not None

    assert User.__meta__.columns.keys() == {"id", "name", "introduce", "age", "money"}
    assert isinstance(User.__meta__.columns["id"].type, sa_types.Integer)
    assert User.__meta__.columns["id"].primary_key
    assert User.__meta__.columns["id"].autoincrement
    assert (
        isinstance(User.__meta__.columns["name"].type, AutoString)
        and User.__meta__.columns["name"].type.length == 30
    )
    assert isinstance(User.__meta__.columns["introduce"].type, sa_types.Text)
    assert isinstance(User.__meta__.columns["age"].type, sa_types.Integer)
    assert isinstance(User.__meta__.columns["money"].type, sa_types.Float)

    assert User.__meta__.constraints == []
    assert not User.__meta__.abstract

    assert User.model_fields.keys() == {"id", "name", "introduce", "age", "money"}
    assert isinstance(User.model_fields["id"], BaseField)
    assert User.model_fields["id"].primary_key
    assert User.model_fields["id"].autoincrement
    assert not User.model_fields["id"].nullable
    assert isinstance(User.model_fields["name"], BaseField)
    assert isinstance(User.model_fields["introduce"], BaseField)
    assert isinstance(User.model_fields["age"], BaseField)
    assert isinstance(User.model_fields["money"], BaseField)

    assert User.__meta__.primary_key == ("id",)
    assert User.__meta__.related_fields == {}
    assert User.__meta__.reverse_related_fields == {}
    assert User.__meta__.foreign_keys == ()
    assert User.__meta__.use_array_in_postgres
    assert User.__meta__.use_jsonb_in_postgres

    assert User.id is User.__meta__.columns["id"]
    assert User.name is User.__meta__.columns["name"]
    assert User.introduce is User.__meta__.columns["introduce"]
    assert User.age is User.__meta__.columns["age"]
    assert User.money is User.__meta__.columns["money"]


@pytest.mark.asyncio
async def test_one_to_many():
    assert Student.__meta__.columns.keys() == {"id", "name", "school"}
    assert (
        isinstance(Student.school, RelatedModelProxy)
        and Student.school.related_model is School
    )
    assert Student.School_id is Student.__meta__.columns["school"]  # type: ignore
    assert isinstance(
        Student.__meta__.columns["school"].type,
        (sa_types.NullType, sa_types.Integer),
    )
    assert Student.__meta__.columns["school"].name == "School_id"
    assert isinstance(Student.model_fields["school"], ForeignKeyField)
    assert Student.__meta__.related_fields == {
        "school": Student.model_fields["school"],
    }

    assert School.__meta__.columns.keys() == {"id", "name"}
    assert (
        isinstance(School.students, RelatedModelProxy)
        and School.students.related_model is Student
    )
    assert isinstance(
        School.model_fields["students"],
        ReverseRelationshipField,
    )
    assert School.__meta__.reverse_related_fields == {
        "students": School.model_fields["students"],
    }


@pytest.mark.asyncio
async def test_many_to_many():
    assert Tag.__meta__.columns.keys() == {"name"}
    assert isinstance(Tag.posts, RelatedModelProxy) and Tag.posts.related_model is Post
    assert isinstance(Tag.model_fields["posts"], ManyToManyField)
    assert Tag.__meta__.many_to_many_fields == {
        "posts": Tag.model_fields["posts"],
    }
    tag_field = Tag.model_fields["posts"]
    assert tag_field.m2m_field_name == "name"
    assert tag_field.m2m_table_field_name == "Tag_name"

    assert Post.__meta__.columns.keys() == {"id", "title"}
    assert isinstance(Post.tags, RelatedModelProxy) and Post.tags.related_model is Tag
    assert isinstance(Post.model_fields["tags"], ManyToManyField)
    assert Post.__meta__.many_to_many_fields == {
        "tags": Post.model_fields["tags"],
    }
    post_field = Post.model_fields["tags"]
    assert post_field.m2m_field_name == "id"
    assert post_field.m2m_table_field_name == "Post_id"

    assert tag_field.table is post_field.table
    assert tag_field.table.name == "Post_Tag"
