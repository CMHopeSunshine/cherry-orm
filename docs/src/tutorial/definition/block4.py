from datetime import date
from typing import Optional

import cherry


class User(cherry.Model):
    id: Optional[int] = cherry.Field(default=None, primary_key=True, autoincrement=True)
    name: cherry.Unique[str]
    age: cherry.Index[int] = 18
    birthday: date = cherry.Field(default_factory=date.today)
