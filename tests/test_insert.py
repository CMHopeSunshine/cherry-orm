import cherry.exception
from tests.models import Post, School, Student, Tag, User

import pytest


@pytest.mark.asyncio
async def test_auto_int_pk():
    user1 = User(name="John", introduce="", age=30, money=100)
    assert user1.id is None
    await user1.insert()
    assert user1.id == 1

    user2 = User(name="Jane", introduce="", age=25, money=200)
    assert user2.id is None
    await user2.insert()
    assert user2.id == 2

    user3 = User(id=3, name="Bob", introduce="", age=20, money=300)
    assert user3.id == 3
    await user3.insert()
    assert user3.id == 3


@pytest.mark.asyncio
async def test_one_to_many():
    school1 = await School(name="school 1").insert()

    student1 = await Student(name="student 1", school=school1).insert()
    assert student1.school == school1

    student2 = await Student(name="student 2", school=school1).insert()
    assert student2.school == school1

    await school1.fetch_related()
    assert [s.id for s in school1.students] == [student1.id, student2.id]

    student3 = await Student(name="student 3").insert()
    student4 = await Student(name="student 4").insert()

    school2 = await School(name="school 2", students=[student3, student4]).insert()

    await student3.fetch_related()
    await student4.fetch_related()
    assert school2.students[0].id == student3.id
    assert school2.students[1].id == student4.id

    student5 = await Student(
        name="student 5",
        school=School(name="school 3"),
    ).insert_with_related()
    assert student5.school and student5.school.id == 3

    student6 = Student(name="student 6")
    student7 = Student(name="student 7")
    school4 = await School(
        name="school 4",
        students=[student6, student7],
    ).insert_with_related()
    assert school4.id == 4
    assert (
        school4.students[0].id == student6.id and school4.students[1].id == student7.id
    )


@pytest.mark.asyncio
async def test_many_to_many():
    tag1 = await Tag(name="tag 1").insert()
    tag2 = await Tag(name="tag 2").insert()
    post1 = await Post(title="post 1").insert()
    post2 = await Post(title="post 2").insert()

    user = User(name="John", introduce="", age=30, money=100)

    await post1.add(tag1)
    await post1.add(tag2)
    await post2.add(tag1)
    await post2.add(tag2)
    assert post1.tags == post2.tags == [tag1, tag2]

    await tag1.fetch_related()
    await tag2.fetch_related()
    assert tag1.posts == tag2.posts

    with pytest.raises(cherry.exception.FieldTypeError):
        await post1.add(user)
        await tag1.add(user)
