import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str

    class Meta:
        database = db
        tablename = "user"


async def main():
    await db.init()

    user = await User(name="Paimon").insert()
    await user.delete()

    user1 = await User(name="user 1").insert()
    user2 = await User(name="user 2").insert()
    user3 = await User(name="user 3").insert()

    await User.delete_many(user1, user2, user3)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
