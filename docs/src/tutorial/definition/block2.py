from datetime import date

import cherry


class User(cherry.Model):
    id: int = cherry.Field(primary_key=True)
    name: str = cherry.Field(unique=True)
    age: int = cherry.Field(default=18, index=True)
    birthday: date = cherry.Field(default_factory=date.today)
