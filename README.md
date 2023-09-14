<p align="center">
    <h1 align="center">Cherry ORM</h1>
    <p align="center">Python 异步 ORM</p>
</p>
<p align="center">
    <a href="./LICENSE">
        <img src="https://img.shields.io/github/license/CMHopeSunshine/cherry-orm.svg" alt="license">
    </a>
    <a href="https://pypi.python.org/pypi/cherry-orm">
        <img src="https://img.shields.io/pypi/v/cherry-orm.svg" alt="pypi">
    </a>
    <a href="https://www.python.org/">
        <img src="https://img.shields.io/badge/python-3.8+-blue.svg" alt="python">
    </a>
</p>

## 简介

`Cherry ORM` 是一个 Python 的异步对象关系映射（ORM）库，它基于 [SQLAlchemy Core](https://www.sqlalchemy.org/) 和 [Pydantic V1](https://docs.pydantic.dev/1.10/) 构建。

它的一切设计都是为了简单易用，极大地减少开发者的数据库操作成本，提高开发效率，让开发者更专注于业务逻辑的实现。

## 安装

- 使用 pip: `pip install cherry-orm`
- 使用 Poetry: `poetry add cherry-orm`
- 使用 PDM: `pdm add cherry-orm`

## 文档

-> [文档地址](https://cherry.cherishmoon.fun)

## 示例

```python
from datetime import date
from typing import List, Optional

import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class Student(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True, index=True)
    age: int
    birthday: date = cherry.Field(default_factory=date.today)
    school: cherry.ForeignKey[Optional["School"]] = None

    class Meta:
        database = db
        tablename = "student"


class School(cherry.Model):
    id: cherry.PrimaryKey[int]
    name: str = cherry.Field(unique=True, index=True)
    students: cherry.ReverseRelation[List[Student]] = []

    class Meta:
        database = db
        tablename = "school"


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

    students: List[Student] = await Student.filter(Student.age >= 18).all()

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
```
