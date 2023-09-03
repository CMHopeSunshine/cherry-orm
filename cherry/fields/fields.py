import datetime
from decimal import Decimal
from enum import Enum
import ipaddress
from pathlib import Path
from typing import Any, Dict, Optional, Type, TYPE_CHECKING, TypeVar, Union
from typing_extensions import Annotated, Self
from uuid import UUID

from .types import AutoString, GUID

from pydantic.fields import FieldInfo, Undefined
from pydantic.main import BaseModel
from pydantic.typing import NoArgAnyCallable
from sqlalchemy import Column
import sqlalchemy.types as sa_type

if TYPE_CHECKING:
    from cherry.models import Model

    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

T = TypeVar("T")

PrimaryKey = Annotated[T, "primary_key"]


class BaseField(FieldInfo):
    def __init__(self, default: Any = ..., **kwargs: Any) -> None:
        self.name: Optional[str] = kwargs.pop("name", None)
        self.type: Optional[Type[Any]] = kwargs.pop("type", None)

        self.primary_key: bool = kwargs.pop("primary_key", False)
        self.autoincrement: bool = kwargs.pop("autoincrement", False)
        self.index: bool = kwargs.pop("index", False)
        self.column_type: Optional[Column] = kwargs.pop("column_type", None)
        self.unique: bool = kwargs.pop("unique", False)
        self.nullable: Optional[bool] = kwargs.pop("nullable", None)
        self.sa_column_args: Dict[str, Any] = kwargs.pop("sa_column_args", {}) or {}
        super().__init__(default, **kwargs)

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]

    @classmethod
    def from_base_field_info(cls, field_info: FieldInfo) -> Self:
        return cls(
            default=field_info.default,
            default_factory=field_info.default_factory,
            alias=field_info.alias,
            alias_priority=field_info.alias_priority,
            title=field_info.title,
            description=field_info.description,
            exclude=field_info.exclude,
            include=field_info.include,
            const=field_info.const,
            gt=field_info.gt,
            ge=field_info.ge,
            lt=field_info.lt,
            le=field_info.le,
            multiple_of=field_info.multiple_of,
            allow_inf_nan=field_info.allow_inf_nan,
            max_digits=field_info.max_digits,
            decimal_places=field_info.decimal_places,
            min_items=field_info.min_items,
            max_items=field_info.max_items,
            unique_items=field_info.unique_items,
            min_length=field_info.min_length,
            max_length=field_info.max_length,
            allow_mutation=field_info.allow_mutation,
            regex=field_info.regex,
            discriminator=field_info.discriminator,
            repr=field_info.repr,
            **field_info.extra,
        )

    def to_sqlalchemy_column(self) -> Column:
        if self.column_type is not None:
            return self.column_type
        if self.type is None:
            raise ValueError("type is required")
        if issubclass(self.type, int):
            type_ = sa_type.Integer
        elif issubclass(self.type, str):
            if self.max_length:
                type_ = AutoString(length=self.max_length)
            else:
                type_ = AutoString
        elif issubclass(self.type, float):
            type_ = sa_type.Float
        elif issubclass(self.type, bool):
            type_ = sa_type.Boolean
        elif issubclass(self.type, datetime.datetime):
            type_ = sa_type.DateTime
        elif issubclass(self.type, datetime.date):
            type_ = sa_type.Date
        elif issubclass(self.type, datetime.time):
            type_ = sa_type.Time
        elif issubclass(self.type, datetime.timedelta):
            type_ = sa_type.Interval
        elif issubclass(self.type, bytes):
            type_ = sa_type.LargeBinary
        elif issubclass(
            self.type,
            (
                Path,
                ipaddress.IPv4Address,
                ipaddress.IPv4Network,
                ipaddress.IPv6Address,
                ipaddress.IPv6Network,
            ),
        ):
            type_ = AutoString
        elif issubclass(self.type, UUID):
            type_ = GUID
        elif issubclass(self.type, Enum):
            type_ = sa_type.Enum(self.type)
        elif issubclass(self.type, Decimal):
            type_ = sa_type.Numeric(
                precision=getattr(self.type, "max_digits", None),
                scale=getattr(self.type, "decimal_places", None),
            )
        elif issubclass(self.type, (list, dict, tuple, set, BaseModel)):
            type_ = sa_type.JSON
        else:
            raise TypeError(
                f"Field {self.name}'s type {self.type} has no matching SQLAlchemy type",
            )

        return Column(
            self.name,
            type_,
            primary_key=self.primary_key,
            autoincrement=self.autoincrement,
            index=self.index,
            unique=self.unique,
            default=self.default or None,
            nullable=self.nullable,
            **self.sa_column_args,
        )


class ForeignKeyField(FieldInfo):
    related_model: Type["Model"]
    foreign_key: str  #  example: "user.id"
    foreign_key_self_name: str  # example: "user_id"
    foreign_key_field_name: str  # example: "id"
    related_field: str  # example: "user"

    def __init__(self, related_field: Any, foreign_key: Any, **kwargs: Any) -> None:
        self.related_field: str = (
            related_field.name
            if isinstance(related_field, Column)
            else str(related_field)
        )
        self.foreign_key: str = (
            f"{foreign_key.table.name}.{foreign_key.name}"
            if isinstance(foreign_key, Column)
            else str(foreign_key)
        )
        self.foreign_key_field_name: str = self.foreign_key.split(".")[-1]
        self.nullable: bool = kwargs.pop("nullable", False)
        super().__init__(**kwargs)

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]


class RelationshipField(FieldInfo):
    related_model: Type["Model"]
    related_field: str
    is_list: bool

    def __init__(self, related_field: Any, **kwargs: Any) -> None:
        self.related_field: str = (
            related_field.name
            if isinstance(related_field, Column)
            else str(related_field)
        )
        self.nullable: bool = kwargs.pop("nullable", False)
        super().__init__(**kwargs)

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]


class ManyToManyField(FieldInfo):
    ...


def Field(
    default: Any = Undefined,
    *,
    primary_key: bool = False,
    autoincrement: bool = False,
    index: bool = False,
    column_type: Optional[Column] = None,
    unique: bool = False,
    nullable: bool = False,
    sa_column_args: Optional[Dict[str, Any]] = None,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny", Any]] = None,
    include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny", Any]] = None,
    const: Optional[bool] = None,
    gt: Optional[float] = None,
    ge: Optional[float] = None,
    lt: Optional[float] = None,
    le: Optional[float] = None,
    multiple_of: Optional[float] = None,
    allow_inf_nan: Optional[bool] = None,
    max_digits: Optional[int] = None,
    decimal_places: Optional[int] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    unique_items: Optional[bool] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    allow_mutation: bool = True,
    regex: Optional[str] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    **extra: Any,
) -> Any:
    nullable = False if primary_key else nullable
    field_info = BaseField(
        default=default,
        default_factory=default_factory,
        primary_key=primary_key,
        autoincrement=autoincrement,
        index=index,
        column_type=column_type,
        unique=unique,
        nullable=nullable,
        sa_column_args=sa_column_args,
        alias=alias,
        title=title,
        description=description,
        exclude=exclude,
        include=include,
        const=const,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        min_items=min_items,
        max_items=max_items,
        unique_items=unique_items,
        min_length=min_length,
        max_length=max_length,
        allow_mutation=allow_mutation,
        regex=regex,
        discriminator=discriminator,
        repr=repr,
        **extra,
    )
    field_info._validate()
    return field_info


def Relationship(
    related_field: Any,
    *,
    foreign_key: Optional[Any] = None,
    nullable: bool = False,
    default_factory: Optional[NoArgAnyCallable] = None,
    alias: Optional[str] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    exclude: Optional[Union["AbstractSetIntStr", "MappingIntStrAny", Any]] = None,
    include: Optional[Union["AbstractSetIntStr", "MappingIntStrAny", Any]] = None,
    discriminator: Optional[str] = None,
    repr: bool = True,
    **extra: Any,
) -> Any:
    if foreign_key is not None:
        field_info = ForeignKeyField(
            foreign_key=foreign_key,
            related_field=related_field,
            default_factory=default_factory,
            nullable=nullable,
            alias=alias,
            title=title,
            description=description,
            exclude=exclude,
            include=include,
            discriminator=discriminator,
            repr=repr,
            **extra,
        )
    else:
        field_info = RelationshipField(
            related_field=related_field,
            default_factory=default_factory,
            nullable=nullable,
            alias=alias,
            title=title,
            description=description,
            exclude=exclude,
            include=include,
            discriminator=discriminator,
            repr=repr,
            **extra,
        )
    field_info._validate()
    return field_info
