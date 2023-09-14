import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class User(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    age: int = 18

    class Meta:
        database = db
        tablename = "user"


async def main():
    await db.init()

    user = User(name="user 1")
    await user.insert()

    user2 = User(name="user 2")
    user3 = User(name="user 3")
    user4 = User(name="user 4")
    await User.insert_many(user2, user3, user4)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
