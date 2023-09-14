from typing import List, Optional

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class Student(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    school: cherry.ForeignKey[Optional["School"]] = None

    class Meta:
        database = db
        tablename = "student"


class School(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    students: cherry.ReverseRelation[List[Student]] = []

    class Meta:
        database = db
        tablename = "school"


async def main():
    await db.init()

    school = School(name="school 1")
    await school.insert()

    await Student(name="student 1", school=school).insert()

    school2 = School(
        name="school 2",
        students=[
            Student(name="student 2"),
            Student(name="student 3"),
        ],
    )
    await school2.insert_with_related()

    student4 = Student(name="student 4", school=School(name="school 3"))
    await student4.insert_with_related()

    # Pythonic Style
    student: List[Student] = await Student.filter(School.name == "school 2").all()
    # Django Style
    student: List[Student] = await Student.filter(school_name="school 2").all()

    student_with_school: Student = (
        await Student.filter(Student.name == "student 1")
        .prefetch_related(Student.school)
        .get()
    )

    school_with_students: School = (
        await School.filter(School.name == "school 2")
        .prefetch_related(School.students)
        .get()
    )

    schools_with_students: List[School] = (
        await School.select_related().prefetch_related(School.students).all()
    )

    school = await School.get(name="school 3")
    await school.fetch_related(School.students)
    assert len(school.students) == 1


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
