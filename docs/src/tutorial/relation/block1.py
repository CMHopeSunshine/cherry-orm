import cherry

db = cherry.Database("sqlite+aiosqlite:///:memory:")


class UserDetail(cherry.Model):
    id: cherry.AutoIntPK = None
    age: int
    address: str
    email: str
    user: cherry.ForeignKey["User"]

    cherry_config = cherry.CherryConfig(tablename="user_detail", database=db)


class User(cherry.Model):
    id: cherry.AutoIntPK = None
    name: str
    detail: cherry.ReverseRelation[UserDetail]

    cherry_config = cherry.CherryConfig(tablename="user", database=db)
