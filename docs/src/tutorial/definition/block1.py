from datetime import date

import cherry


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str
    age: int = 18
    birthday: date
