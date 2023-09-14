from typing import Any, Dict, List, Optional, Tuple

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True)
    age: int

    class Meta:
        database = db
        tablename = "user"


async def main():
    await db.init()

    users = [User(id=i, name=f"user {i}", age=i * 5) for i in range(1, 11)]
    await User.insert_many(*users)

    # Pythonic 风格
    user: User = await User.get(User.id == 1)
    # Django 风格
    user: User = await User.get(id=1)

    # Pythonic 风格
    user_or_none: Optional[User] = await User.get_or_none(User.name == "user 2")
    # Django 风格
    user_or_none: Optional[User] = await User.get_or_none(name="user 2")

    # Pythonic 风格
    user: User = await User.get_or_create(
        User.name == "user 3",
        defaults={"id": 3, "age": 15},
    )
    # Django 风格
    user: User = await User.get_or_create(
        name="user 3",
        defaults={"id": 3, "age": 15},
    )

    # Pythonic 风格
    user1: Optional[User] = await User.filter(User.age <= 15).first()
    users: List[User] = await User.filter(User.age > 10).all()
    user2: User = await User.filter(User.name == "user 1").get()
    user3: Optional[User] = await User.filter(User.age >= 5).random_one()
    usersp: List[User] = await User.filter(User.age <= 5).paginate(page=1, page_size=3)

    # Django 风格
    user1: Optional[User] = await User.filter(age__le=15).first()
    users: List[User] = await User.filter(age__gt=10).all()
    user2: User = await User.filter(name="user 1").get()
    user3: Optional[User] = await User.filter(age__ge=5).random_one()
    usersp: List[User] = await User.filter(age__ge=5).paginate(page=1, page_size=3)

    user1 = await User.filter(User.age <= 15).order_by(User.age).first()
    users = await User.filter(User.age > 15).limit(3).all()
    users = await User.filter(User.age > 15).offset(1).all()

    user_name_and_age: Optional[Tuple[str, int]] = (
        await User.filter().values(User.name, User.age).first()
    )
    user_name_list: List[str] = (
        await User.filter().values(User.name, flatten=True).all()
    )
    user_name: str = (
        await User.filter(User.age == 15).values(User.name, flatten=True).get()
    )

    user_dict: Optional[Dict[str, Any]] = await User.filter().value_dict().first()
    user_name_and_age_dict: List[Dict[str, Any]] = (
        await User.filter().value_dict(User.name, User.age).all()
    )

    all_user: List[User] = await User.all()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
