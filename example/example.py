from datetime import date
from typing import Optional

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class Student(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True, index=True)
    age: int
    birthday: date = cherry.Field(default_factory=date.today)
    school: cherry.ForeignKey[Optional["School"]] = None

    cherry_config = cherry.CherryConfig(tablename="student", database=db)


class School(cherry.Model):
    id: cherry.PrimaryKey[int]
    name: str = cherry.Field(unique=True, index=True)
    students: cherry.ReverseRelation[list[Student]] = []

    cherry_config = cherry.CherryConfig(tablename="school", database=db)


async def main():
    await db.init()

    # 插入
    school = await School(id=1, name="school 1").insert()
    student1 = await Student(id=1, name="student 1", age=15, school=school).insert()
    await Student(id=2, name="student 2", age=18, school=school).insert()
    await Student(id=3, name="student 3", age=20, school=school).insert()

    # 更新
    student1.age += 1
    await student1.save()
    # or
    await student1.update(age=19)

    # 获取关联的模型
    await school.fetch_related(School.students)
    assert len(school.students) == 3

    # 条件查询
    # Pythonic 风格
    student2: Student = await Student.filter(Student.name == "student 2").get()
    # Django 风格
    student2: Student = await Student.filter(name="student 2").get()

    students: list[Student] = await Student.filter(Student.age >= 18).all()

    # 聚合查询
    student_nums: int = await Student.filter(Student.age >= 18).count()
    assert len(students) == student_nums
    student_age_avg: Optional[int] = await Student.select().avg(Student.age)

    # 查询时预取关联模型
    student_with_school: Student = (
        await Student.filter(Student.name == "student 3")
        .prefetch_related(Student.school)
        .get()
    )

    # 选择更新
    await Student.select().update(birthday=date(2023, 10, 1))
    # 选择删除
    await Student.filter(Student.age >= 20).delete()
