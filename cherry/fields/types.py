import datetime
from decimal import Decimal
from enum import Enum
import inspect
import ipaddress
from pathlib import Path
from typing import Any, cast, Iterable, Mapping
from uuid import UUID

from cherry.exception import FieldTypeError

from pydantic.fields import ModelField
from pydantic.main import BaseModel
from pydantic.typing import all_literal_values, get_args, get_origin, is_literal_type
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import ARRAY as saARRAY
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.sql.type_api import TypeEngine


class AutoString(types.TypeDecorator):
    impl = types.String
    cache_ok = True
    mysql_default_length = 255

    def load_dialect_impl(self, dialect: Dialect) -> types.TypeEngine[Any]:
        impl = cast(types.String, self.impl)
        if impl.length is None and dialect.name == "mysql":
            return dialect.type_descriptor(types.String(self.mysql_default_length))
        return super().load_dialect_impl(dialect)


class Array(types.TypeDecorator):
    impl = types.JSON
    cache_ok = True

    def __init__(self, inner_type: Any, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.inner_type = inner_type

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(saARRAY(self.inner_type))
        return dialect.type_descriptor(types.JSON())


def get_sqlalchemy_type_from_python_type(type_: type):
    if issubclass(type_, bool):
        return types.Boolean
    elif issubclass(type_, Enum):
        return types.Enum(type_)
    if issubclass(type_, int):
        return types.Integer
    elif issubclass(type_, float):
        return types.Float
    elif issubclass(type_, str):
        return AutoString
    elif issubclass(type_, datetime.datetime):
        return types.DateTime
    elif issubclass(type_, datetime.date):
        return types.Date
    elif issubclass(type_, datetime.time):
        return types.Time
    elif issubclass(type_, datetime.timedelta):
        return types.Interval
    elif issubclass(type_, bytes):
        return types.LargeBinary
    elif issubclass(
        type_,
        (
            Path,
            ipaddress._BaseAddress,
            ipaddress._BaseNetwork,
        ),
    ):
        return AutoString
    elif issubclass(type_, UUID):
        return types.Uuid
    elif issubclass(type_, Decimal):
        return types.Numeric(
            precision=getattr(type_, "max_digits", None),
            scale=getattr(type_, "decimal_places", None),
        )
    else:
        return None


def get_sqlalchemy_type_from_field(field: ModelField):
    if is_literal_type(field.type_):
        values = all_literal_values(field.type_)
        if all(issubclass(type(v), type(values[0])) for v in values[1:]):
            if (
                type_ := get_sqlalchemy_type_from_python_type(type(values[0]))
            ) is not None:
                return type_, False
            raise FieldTypeError(
                f"{field.type_} has no matching SQLAlchemy type",
            )
        raise FieldTypeError(
            f"{field.type_} All values in a literal type must be of the same type",
        )
    if (origin_type := get_origin(field.annotation)) is not None:
        if issubclass(origin_type, Iterable):
            args = get_args(field.annotation)
            if not args:
                return types.JSON, True
            elif (
                get_origin(args[0]) is None
                and (
                    len(args) == 1
                    or (
                        issubclass(origin_type, tuple)
                        and (
                            args[1] is ...
                            or all(issubclass(arg, args[0]) for arg in args[1:])
                        )
                    )
                )
                and (inner_type := get_sqlalchemy_type_from_python_type(args[0]))
                is not None
            ):
                return Array(inner_type), True
        if issubclass(origin_type, Mapping):
            return types.JSON, True
    if issubclass(field.type_, str):
        if getattr(field.field_info, "long_text", False):
            return types.Text, False
        else:
            return AutoString(length=field.field_info.max_length), False
    if (type_ := get_sqlalchemy_type_from_python_type(field.type_)) is not None:
        return type_, False
    if inspect.isclass(field.type_) and issubclass(field.type_, BaseModel):
        return types.JSON, True
    raise FieldTypeError(
        f"{field.type_} has no matching SQLAlchemy type",
    )
