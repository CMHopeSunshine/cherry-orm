import datetime
from decimal import Decimal
from enum import Enum
import ipaddress
from pathlib import Path
from typing import Any, cast, Optional, Union
from uuid import UUID

from cherry.exception import FieldTypeError
from cherry.meta.config import CherryMeta

from annotated_types import MaxLen
from khemia.typing import (
    all_literal_values,
    check_isinstance,
    check_issubclass,
    get_args,
    get_args_without_none,
    is_annotated,
    is_dataclass,
    is_iterable_type,
    is_literal_type,
    is_mapping_type,
    is_none_type,
    is_sequence_type,
)
from pydantic.fields import FieldInfo
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


def sa_to_py_type(type_: type[Any], config: CherryMeta):
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
        or is_mapping_type(type_)
        or is_sequence_type(type_)
    ):
        return Json(config.use_jsonb_in_postgres)
    else:
        return None


def get_sqlalchemy_type_from_field(
    field_info: FieldInfo,
    config: CherryMeta,
) -> tuple[bool, Union[type[TypeEngine], TypeEngine], bool]:
    if not field_info.annotation or is_none_type(field_info.annotation):
        raise FieldTypeError("field type can not be None")
    if is_annotated(field_info.annotation):
        type_ = get_args(field_info.annotation)[0]
    else:
        type_ = field_info.annotation
    is_optional, types_ = get_args_without_none(type_)
    if not types_:
        raise FieldTypeError(
            f"{type_} has no matching SQLAlchemy type",
        )
    type_ = types_[0]
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
        _, arg_python_types = get_args_without_none(args[0])
        if not arg_python_types:
            return is_optional, Json(config.use_jsonb_in_postgres), True
        if arg_type := sa_to_py_type(arg_python_types[0], config):
            return is_optional, Array(arg_type), True
        return is_optional, Json(config.use_jsonb_in_postgres), True
    if issubclass(type_, str):
        if getattr(field_info, "long_text", False):
            return is_optional, types.Text, False
        else:
            return (
                is_optional,
                AutoString(length=get_field_max_length(field_info)),
                False,
            )
    if (type_ := sa_to_py_type(type_, config)) is not None:
        return is_optional, type_, False
    if is_dataclass(type_):
        return is_optional, Json(config.use_jsonb_in_postgres), True
    raise FieldTypeError(
        f"{type_} has no matching SQLAlchemy type",
    )


def get_field_max_length(field_info: FieldInfo) -> Optional[int]:
    for metadata in field_info.metadata:
        if check_isinstance(metadata, MaxLen):
            return metadata.max_length
    return None
