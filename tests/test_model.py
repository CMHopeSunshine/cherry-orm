from cherry.fields.fields import BaseField
from cherry.fields.types import AutoString
from cherry.meta import MetaConfig
from tests.database import database
from tests.models import User

import pytest
import sqlalchemy.types as sa_types


@pytest.mark.asyncio
async def test_meta():
    assert User.__fields__.keys() == {"id", "name", "age", "money"}
    assert issubclass(User.__meta__, MetaConfig)
    assert User.__meta__.tablename == "User"
    assert User.__meta__.database == database
    assert User.__meta__.table is not None
    assert User.__meta__.metadata is not None

    assert User.__meta__.columns.keys() == {"id", "name", "age", "money"}
    assert isinstance(User.__meta__.columns["id"].type, sa_types.Integer)
    assert User.__meta__.columns["id"].primary_key
    assert User.__meta__.columns["id"].autoincrement
    assert isinstance(User.__meta__.columns["name"].type, AutoString)
    assert isinstance(User.__meta__.columns["age"].type, sa_types.Integer)
    assert isinstance(User.__meta__.columns["money"].type, sa_types.Float)

    assert User.__meta__.constraints == []
    assert not User.__meta__.abstract

    assert User.__meta__.model_fields.keys() == {"id", "name", "age", "money"}
    assert isinstance(User.__meta__.model_fields["id"], BaseField)
    assert User.__meta__.model_fields["id"].primary_key
    assert User.__meta__.model_fields["id"].autoincrement
    assert not User.__meta__.model_fields["id"].nullable
    assert isinstance(User.__meta__.model_fields["name"], BaseField)
    assert isinstance(User.__meta__.model_fields["age"], BaseField)
    assert isinstance(User.__meta__.model_fields["money"], BaseField)

    assert User.__meta__.primary_key == ("id",)
    assert User.__meta__.related_fields == {}
    assert User.__meta__.back_related_fields == {}
    assert User.__meta__.foreign_keys == ()
