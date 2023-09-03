from tests.models import User

import pytest


@pytest.mark.asyncio
async def test_auto_int_pk():
    user1 = User(name="John", age=30, money=100)
    assert user1.id is None
    await user1.insert()
    assert user1.id == 1

    user2 = User(name="Jane", age=25, money=200)
    assert user2.id is None
    await user2.insert()
    assert user2.id == 2

    user3 = User(id=3, name="Bob", age=20, money=300)
    assert user3.id == 3
    await user3.insert()
    assert user3.id == 3
