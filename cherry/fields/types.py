import datetime
from decimal import Decimal
from enum import Enum
import ipaddress
from pathlib import Path
from typing import Any, cast, Tuple, Type, Union
from uuid import UUID

from cherry.exception import FieldTypeError
from cherry.meta import MetaConfig

from khemia.typing import (
    all_literal_values,
    check_issubclass,
    get_args,
    get_type_from_optional,
    is_annotated,
    is_dataclass,
    is_iterable_type,
    is_json_like_type,
    is_literal_type,
    is_mapping_type,
)
from pydantic.fields import ModelField
from pydantic.main import BaseModel
from sqlalchemy import types
from sqlalchemy.dialects.postgresql import (
    ARRAY as pgARRAY,
    JSONB as pgJSONB,
)
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
            return dialect.type_descriptor(pgARRAY(self.inner_type))
        return dialect.type_descriptor(types.JSON())


class Json(types.TypeDecorator):
    impl = types.JSON
    cache_ok = True

    def __init__(self, use_jsonb: bool, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.use_jsonb = use_jsonb

    def load_dialect_impl(self, dialect: Dialect) -> TypeEngine:
        if dialect.name == "postgresql" and self.use_jsonb:
            return dialect.type_descriptor(pgJSONB())
        return dialect.type_descriptor(types.JSON())


def sa_to_py_type(type_: Type[Any], config: Type[MetaConfig]):
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
    elif (
        is_dataclass(type_)
        or check_issubclass(type_, BaseModel)
        or is_json_like_type(type_)
    ):
        return Json(config.use_jsonb_in_postgres)
    else:
        return None


def get_sqlalchemy_type_from_field(
    field: ModelField,
    config: Type[MetaConfig],
) -> Tuple[bool, Union[Type[TypeEngine], TypeEngine], bool]:
    if is_annotated(field.annotation):
        type_ = get_args(field.annotation)[0]
    else:
        type_ = field.annotation
    is_optional, type_ = get_type_from_optional(type_)
    if is_literal_type(type_):
        values = all_literal_values(type_)
        if all(issubclass(type(v), type(values[0])) for v in values[1:]):
            if (type_ := sa_to_py_type(type(values[0]), config)) is not None:
                return is_optional, type_, False
            raise FieldTypeError(
                f"{type_} has no matching SQLAlchemy type",
            )
        raise FieldTypeError(
            f"{type_} All values in a literal type must be of the same type",
        )
    if (
        is_mapping_type(type_)
        or is_dataclass(type_)
        or check_issubclass(type_, BaseModel)
    ):
        return is_optional, Json(config.use_jsonb_in_postgres), True
    elif is_iterable_type(type_) and not check_issubclass(type_, str):
        if not config.use_array_in_postgres:
            return is_optional, Json(config.use_jsonb_in_postgres), True
        args = get_args(type_)
        if not args:
            return is_optional, Json(config.use_jsonb_in_postgres), True
        _, arg_python_type = get_type_from_optional(args[0])
        if arg_type := sa_to_py_type(arg_python_type, config):
            return is_optional, Array(arg_type), True
        return is_optional, Json(config.use_jsonb_in_postgres), True
    if issubclass(type_, str):
        if getattr(field.field_info, "long_text", False):
            return is_optional, types.Text, False
        else:
            return is_optional, AutoString(length=field.field_info.max_length), False
    if (type_ := sa_to_py_type(type_, config)) is not None:
        return is_optional, type_, False
    if is_dataclass(type_):
        return is_optional, Json(config.use_jsonb_in_postgres), True
    raise FieldTypeError(
        f"{type_} has no matching SQLAlchemy type",
    )
