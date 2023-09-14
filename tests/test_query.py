import cherry.exception
from tests.models import User

import pytest


@pytest.mark.asyncio
async def test_query():
    users = [
        User(id=i, name=f"user {i}", age=i * 5, money=i * 100.0) for i in range(1, 11)
    ]
    await User.insert_many(*users)

    assert await User.all() == users
    assert await User.filter(User.age > 20).all() == users[4:]

    user = await User.get(User.id == 1)
    user2 = await User.get(id=1)
    assert user == user2 == users[0]

    with pytest.raises(cherry.exception.NoMatchDataError):
        user = await User.get(User.id == 11)

    assert await User.get_or_none(User.id == 12) is None

    user = await User.get_or_create(id=2, defaults={"name": "user 2"})
    assert user == users[1]

    user = await User.get_or_create(name="user 12", defaults={"id": 12, "age": 60})
    assert user.id == 12 and user.age == 60

    user = await User.update_or_create(name="user 12", defaults={"age": 100})
    assert user.id == 12 and user.age == 100
    await user.delete()

    user = await User.update_or_create(name="user 13", defaults={"id": 13, "age": 100})
    assert user.id == 13 and user.age == 100
    await user.delete()

    assert await User.filter(User.money >= 500).count() == 6
    assert await User.filter(User.money < 500).max(User.money) == 400.0
    assert await User.filter(User.age < 30).min(User.age) == 5.0
    assert await User.filter(User.age > 30).sum(User.age) == 170
    assert await User.select().avg(User.money) == 550.0
    assert not await User.filter(User.age > 50).exists()
    assert await User.select().coalesce(User.age, User.money).first() == 5
