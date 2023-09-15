from datetime import date

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    age: int = 18
    birthday: date = cherry.Field(default_factory=date.today)

    class Meta:
        database = db
        tablename = "user"


async def main():
    await db.init()

    user = await User(name="Paimon", age=18, birthday=date(2020, 6, 1)).insert()
    user.age += 1
    user.birthday = date(2022, 6, 1)
    await user.save()

    await user.update(age=21, birthday=date(2023, 6, 1))

    user, is_update = await User.update_or_create(
        User.name == "Paimon",
        defaults={"age": 18, "birthday": date(2020, 6, 1)},
    )

    user1 = await User(name="user 1").insert()
    user2 = await User(name="user 2").insert()
    user3 = await User(name="user 3").insert()

    user1.name = "user 1 updated"
    user2.age += 3
    user3.birthday = date(2024, 6, 1)
    await User.save_many(user1, user2, user3)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
