from datetime import date

import cherry


class User(cherry.Model):
    id: cherry.PrimaryKey[int]
    name: cherry.Unique[str]
    age: cherry.Index[int] = 18
    birthday: date = cherry.Field(default_factory=date.today)
