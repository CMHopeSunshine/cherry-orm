from typing import List, Union

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True)
    age: int
    money: int

    class Meta:
        database = db
        tablename = "user"


async def main():
    await db.init()

    users = [
        User(id=i, name=f"user {i}", age=i * 5, money=i * 100) for i in range(1, 11)
    ]
    await User.save_many(*users)

    nums = await User.filter(User.age >= 15).count()
    avg = await User.filter(User.money >= 500).avg(User.money)
    min_age = await User.select().min(User.age)
    max_age = await User.select().max(User.age)
    money_sum = await User.filter(User.age >= 20).sum(User.money)
    c: Union[str, int, None] = (
        await User.select().coalesce(User.name, User.money).first()
    )
    cs: List[Union[str, int, None]] = (
        await User.select().coalesce(User.name, User.money).all()
    )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
