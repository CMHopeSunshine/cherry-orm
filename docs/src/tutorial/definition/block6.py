import cherry

db = cherry.Database("sqlite+aiosqlite:///test.db")


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str
    age: int = 18

    class Meta:
        tablename = "user_table"
        database = db


async def main():
    await db.init()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
