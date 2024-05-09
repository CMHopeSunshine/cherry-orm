<p align="center">
    <h1 align="center">Cherry ORM</h1>
    <p align="center">Python Asynchronous ORM</p>
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

<p align="center">
    <a href="https://github.com/CMHopeSunshine/cherry-orm">简体中文</a>
    ·
    <strong>English</strong>
</p>

## Overview

`Cherry ORM` is an asynchronous object relational mapping (ORM) library for Python. It is based on [SQLAlchemy Core](https://www.sqlalchemy.org/) and [Pydantic V1](https://docs.pydantic.dev/1.10/).

All of its design is designed to be simple and easy to use, greatly reducing the cost of database operation for developers, improving development efficiency, and allowing developers to focus more on the implementation of business logic.


## Install

- use pip: `pip install cherry-orm`
- use Poetry: `poetry add cherry-orm`
- use PDM: `pdm add cherry-orm`

## Document

-> [Document](https://cherry.cherishmoon.top/en/)

## Example

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

    # insert
    school = await School(id=1, name="school 1").insert()
    student1 = await Student(id=1, name="student 1", age=15, school=school).insert()
    await Student(id=2, name="student 2", age=18, school=school).insert()
    await Student(id=3, name="student 3", age=20, school=school).insert()

    # update
    student1.age += 1
    await student1.save()
    # or
    await student1.update(age=19)

    # get related model
    await school.fetch_related(School.students)
    assert len(school.students) == 3

    # conditional  query
    # Pythonic style
    student2: Student = await Student.filter(Student.name == "student 2").get()
    # Django style
    student2: Student = await Student.filter(name="student 2").get()

    students: List[Student] = await Student.filter(Student.age >= 18).all()

    # aggregate query
    student_nums: int = await Student.filter(Student.age >= 18).count()
    assert len(students) == student_nums
    student_age_avg: Optional[int] = await Student.select().avg(Student.age)

    # prefetch related model in query
    student_with_school: Student = (
        await Student.filter(Student.name == "student 3")
        .prefetch_related(Student.school)
        .get()
    )

    # select for update
    await Student.select().update(birthday=date(2023, 10, 1))
    # select for delete
    await Student.filter(Student.age >= 20).delete()
```
