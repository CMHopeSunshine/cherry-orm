import datetime
from decimal import Decimal
from enum import Enum
import ipaddress
from pathlib import Path
from typing import Any, cast, Optional
import uuid
from uuid import UUID

from pydantic.fields import ModelField
from pydantic.main import BaseModel
from sqlalchemy import CHAR, types
from sqlalchemy.dialects.postgresql import UUID as saUUID
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.type_api import TypeEngine
import sqlalchemy.types as sa_type


class AutoString(types.TypeDecorator):
    impl = types.String
    cache_ok = True
    mysql_default_length = 255

    def load_dialect_impl(self, dialect: Dialect) -> types.TypeEngine[Any]:
        impl = cast(types.String, self.impl)
        if impl.length is None and dialect.name == "mysql":
            return dialect.type_descriptor(types.String(self.mysql_default_length))
        return super().load_dialect_impl(dialect)


class GUID(types.TypeDecorator):
    """Platform-independent GUID type.

    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(saUUID())
        return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value).hex
            else:
                # hexstring
                return value.hex

    def process_result_value(self, value: Any, dialect: Dialect) -> Optional[uuid.UUID]:
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(value)
        return cast(uuid.UUID, value)


def get_sqlalchemy_type_from_field(field: ModelField):
    if issubclass(field.type_, int):
        return sa_type.Integer
    elif issubclass(field.type_, str):
        if hasattr(field.field_info, "max_length"):
            return AutoString(length=field.field_info.max_length)
        else:
            return AutoString
    elif issubclass(field.type_, float):
        return sa_type.Float
    elif issubclass(field.type_, bool):
        return sa_type.Boolean
    elif issubclass(field.type_, datetime.datetime):
        return sa_type.DateTime
    elif issubclass(field.type_, datetime.date):
        return sa_type.Date
    elif issubclass(field.type_, datetime.time):
        return sa_type.Time
    elif issubclass(field.type_, datetime.timedelta):
        return sa_type.Interval
    elif issubclass(field.type_, bytes):
        return sa_type.LargeBinary
    elif issubclass(
        field.type_,
        (
            Path,
            ipaddress.IPv4Address,
            ipaddress.IPv4Network,
            ipaddress.IPv6Address,
            ipaddress.IPv6Network,
        ),
    ):
        return AutoString
    elif issubclass(field.type_, UUID):
        return GUID
    elif issubclass(field.type_, Enum):
        return sa_type.Enum(field.type_)
    elif issubclass(field.type_, Decimal):
        return sa_type.Numeric(
            precision=getattr(field.type_, "max_digits", None),
            scale=getattr(field.type_, "decimal_places", None),
        )
    elif issubclass(field.type_, (list, dict, tuple, set, BaseModel)):
        return sa_type.JSON
    else:
        raise TypeError(
            f"{field.type_} has no matching SQLAlchemy type",
        )
