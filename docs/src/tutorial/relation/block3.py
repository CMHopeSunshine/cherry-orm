import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class Tag(cherry.Model):
    id: cherry.AutoIntPK = None
    content: str
    posts: cherry.ManyToMany[list["Post"]] = []

    cherry_config = cherry.CherryConfig(tablename="tag", database=db)


class Post(cherry.Model):
    id: cherry.AutoIntPK = None
    title: str
    tags: cherry.ManyToMany[list[Tag]] = []

    cherry_config = cherry.CherryConfig(tablename="post", database=db)


async def main():
    await db.init()

    tag1 = await Tag(content="tag 1").insert()
    tag2 = await Tag(content="tag 2").insert()

    post1 = await Post(title="post 1").insert()
    post2 = await Post(title="post 2").insert()

    await post1.add(tag1)
    await post1.add(tag2)

    await post2.add(tag1)

    assert post1.tags == [tag1, tag2]
    assert post2.tags == [tag1]

    await tag1.fetch_related(Tag.posts)
    assert len(tag1.posts) == 2

    await post1.remove(tag1)
    assert post1.tags == [tag2]

    await tag1.fetch_related(Tag.posts)
    assert len(tag1.posts) == 1


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
