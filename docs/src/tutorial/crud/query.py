from typing import Any, Optional

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True)
    age: int

    cherry_config = cherry.CherryConfig(tablename="user", database=db)


async def main():
    await db.init()

    users = [User(id=i, name=f"user {i}", age=i * 5) for i in range(1, 11)]
    await User.insert_many(*users)

    # Pythonic style
    user: User = await User.get(User.id == 1)
    # Django style
    user: User = await User.get(id=1)

    # Pythonic style
    user_or_none: Optional[User] = await User.get_or_none(User.name == "user 2")
    # Django style
    user_or_none: Optional[User] = await User.get_or_none(name="user 2")

    # Pythonic style
    user, is_get = await User.get_or_create(
        User.name == "user 3",
        defaults={"id": 3, "age": 15},
    )
    # Django style
    user, is_get = await User.get_or_create(
        name="user 3",
        defaults={"id": 3, "age": 15},
    )

    # Pythonic style
    user1: Optional[User] = await User.filter(User.age <= 15).first()
    users: list[User] = await User.filter(User.age > 10).all()
    user2: User = await User.filter(User.name == "user 1").get()
    user3: Optional[User] = await User.filter(User.age >= 5).random_one()
    usersp: list[User] = await User.filter(User.age <= 5).paginate(page=1, page_size=3)

    # Django style
    user1: Optional[User] = await User.filter(age__le=15).first()
    users: list[User] = await User.filter(age__gt=10).all()
    user2: User = await User.filter(name="user 1").get()
    user3: Optional[User] = await User.filter(age__ge=5).random_one()
    usersp: list[User] = await User.filter(age__ge=5).paginate(page=1, page_size=3)

    user1 = await User.filter(User.age <= 15).order_by(User.age).first()
    users = await User.filter(User.age > 15).limit(3).all()
    users = await User.filter(User.age > 15).offset(1).all()

    user_name_and_age: Optional[tuple[str, int]] = (
        await User.filter().values(User.name, User.age).first()
    )
    user_name_list: list[str] = (
        await User.filter().values(User.name, flatten=True).all()
    )
    user_name: str = (
        await User.filter(User.age == 15).values(User.name, flatten=True).get()
    )

    user_dict: Optional[dict[str, Any]] = await User.filter().value_dict().first()
    user_name_and_age_dict: list[dict[str, Any]] = (
        await User.filter().value_dict(User.name, User.age).all()
    )

    all_user: list[User] = await User.all()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
