import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class UserDetail(cherry.Model):
    id: cherry.AutoIntPK = None
    age: int
    address: str
    email: str
    user: cherry.ForeignKey["User"]

    class Meta:
        database = db
        tablename = "user_detail"


class User(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    detail: cherry.ReverseRelation[UserDetail]

    class Meta:
        database = db
        tablename = "user"
