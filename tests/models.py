from cherry.fields import Field
from cherry.models import Model
from tests.database import database


class User(Model):
    id: int | None = Field(default=None, primary_key=True, autoincrement=True)
    name: str
    age: int
    money: float

    class Meta:
        database = database
