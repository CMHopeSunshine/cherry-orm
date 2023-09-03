import asyncio
from datetime import date
from typing import Optional

from cherry import Database, Field, Model, Relationship
from cherry.fields import AutoIncrementIntPrimaryKey, PrimaryKey

database = Database("sqlite+aiosqlite:///:memory:")
"""创建一个数据库实例对象，传入数据库连接字符串，这里表示使用sqlite内存数据库"""


class School(Model):
    id: int | None = Field(default=None, primary_key=True, autoincrement=True)
    """定义自增主键，默认值为None表示由数据库自动生成"""
    name: str
    built_date: date = Field(default_factory=date.today)
    classes: list["Class"] = Relationship(
        default_factory=list,
        related_field="school",
    )
    """反向外键关联关系，一个学校可以有多个班级"""

    class Meta:
        tablename = "school"
        """数据库中使用的表名"""
        database = database
        """使用的数据库实例对象"""


class Class(Model):
    id: AutoIncrementIntPrimaryKey = None
    """自增主键的简便写法"""
    name: str
    school: Optional[School] = Relationship(
        foreign_key="school.id",
        related_field="classes",
    )
    """外键关系，表示班级所属的学校"""
    students: list["Student"] = Relationship(
        default_factory=list,
        related_field="class_",
    )
    """反向外键关联关系，一个班级可以有多个学生"""

    class Meta:
        tablename = "class"
        database = database


class Student(Model):
    name: PrimaryKey[str]
    """可以用字符串作为主键，PrimaryKey是Field(primary_key=True)的简便写法"""
    age: int = 15
    """可以设置默认值"""
    job: Optional[str] = None
    """可以为空"""
    class_: Optional[Class] = Relationship(
        foreign_key="class.id",
        related_field="students",
    )
    """外键关系，表示学生所属的班级"""

    class Meta:
        tablename = "student"
        database = database


School.update_forward_refs()
Class.update_forward_refs()
# 更新向前引用，使得类型验证和Relationship中的类型提示生效


async def main():
    await database.create_all()  # 在数据库中创建表

    # 插入
    await School(name="school 1", built_date=date(2000, 1, 1)).insert()
    school1 = School(name="school 2")
    await school1.insert()

    class1 = await Class(name="class 1", school=school1).insert()
    class2 = await Class(name="class 2", school=school1).insert()
    student1 = await Student(name="student 1", class_=class1).insert()
    student2 = await Student(name="student 2", age=16, class_=class1).insert()
    student3 = await Student(name="student 3", age=18, class_=class2).insert()
    student4 = await Student(name="student 4", age=14, class_=class2).insert()
    student5 = await Student(name="student 5", age=10, class_=class2).insert()
    student6 = await Student(name="student 6", class_=class2).insert()

    # 更新
    await school1.update(built_date=date(2023, 1, 1))
    student5.age = 20
    await student5.save()

    # 获取关联的数据
    await class1.fetch_related()  # 为空则表示所有，即所属的学校及拥有的学生
    assert class1.school
    assert class1.school.name == "school 2"
    await class2.fetch_related(Class.students)  # 可以指定获取哪些字段
    assert len(class2.students) == 4

    # 删除
    await student6.delete()

    # 从数据库中同步数据
    await class2.fetch()

    # 查询
    school_first = await School.first()  # 查询第一个
    all_class = await Class.all()  # 查询所有

    # 条件查询
    students = await Student.filter(Student.age > 15).all()  # 取所有
    student1 = await Student.filter(Student.name == "student 1").first()  # 取第一个
    student2 = await Student.filter(
        Student.name == "student 2",
    ).get()  # 取第一个，如果没有则抛出异常
    student3 = await Student.query().random_one()  # 取随机一个
    student_data_tuple = (
        await Student.filter(Student.name == "student 3")
        .values(Student.name, Student.job)
        .first()
    )  # 只取部分字段，以元组返回
    student_data_dict = (
        await Student.query().value_dict(Student.name, Student.age).first()
    )  # 只取部分字段，以字典返回
    student_names = (
        await Student.query().values(Student.name, flatten=True).all()
    )  # 只取其中某个字段，以值或值列表返回

    # 关联查询
    await Class.filter(Class.name == "class 1", School.name == "school 1").first()

    # 预取关联的数据
    class_with_students = (
        await Class.filter(
            Class.name == "class 1",
        )
        .prefetch_related(Class.students)
        .first()
    )
    students_and_his_class = (
        await Student.query().prefetch_related(Student.class_).all()
    )

    # 聚合查询
    count = await Student.filter(Student.age >= 15).count()
    max_age = await Student.filter(Class.name == "class 2").max(Student.age)
    avg_age = await Student.query().avg(Student.age)
    sum_age = await Student.query().sum(Student.age)
    await Student.query().offset(2).limit(3).order_by(Student.age).all()

    # 查询并更新、删除
    await School.filter(School.name == "school 1").update(built_date=date.today())
    await Student.filter(Student.age >= 15).update(age=20)
    await Student.filter(Student.age < 15).delete()


if __name__ == "__main__":
    asyncio.run(main())
