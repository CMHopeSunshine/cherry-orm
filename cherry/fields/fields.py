from typing import Any, Dict, Literal, Optional, Type, TYPE_CHECKING, Union
from typing_extensions import Self

from cherry.typing import CASCADE_TYPE

from pydantic.fields import FieldInfo, Undefined
from pydantic.typing import NoArgAnyCallable
from sqlalchemy import Column, Table

if TYPE_CHECKING:
    from cherry.models import Model

    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny


class BaseField(FieldInfo):
    primary_key: bool = False
    autoincrement: bool = False
    index: bool = False
    unique: bool = False
    sa_column: Optional[Column]
    sa_column_extra: Dict[str, Any] = {}
    nullable: Optional[bool] = None
    long_text: bool = False

    def __init__(self, default: Any = ..., **kwargs: Any) -> None:
        self.primary_key = kwargs.pop("primary_key", False)
        self.autoincrement = kwargs.pop("autoincrement", False)
        self.index = kwargs.pop("index", False)
        self.unique = kwargs.pop("unique", False)
        self.nullable = kwargs.pop("nullable", None)
        self.sa_column = kwargs.pop("sa_column", None)
        self.sa_column_extra = kwargs.pop("sa_column_extra", {}) or {}
        self.long_text = kwargs.pop("long_text", False)
        super().__init__(default, **kwargs)

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


class RelationshipField(FieldInfo):
    related_model: Type["Model"]
    related_field_name: str
    related_field: Optional["RelationshipField"]
    on_update: Optional[str]
    on_delete: Optional[str]
    nullable: Optional[bool] = None


class ForeignKeyField(RelationshipField):
    related_field: Optional["ReverseRelationshipField"]
    related_field_name: Optional[str]
    foreign_key: str
    foreign_key_self_name: str
    sa_column_extra: Dict[str, Any]
    foreign_key_extra: Dict[str, Any]

    def __init__(
        self,
        related_field: Optional[str],
        foreign_key: Union[Literal[True], str],
        foreign_key_extra: Optional[Dict[str, Any]],
        on_update: Optional[str],
        on_delete: Optional[str],
        sa_column_extra: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        self.related_field = None  #  generate when generate model column
        self.related_field_name = related_field
        if isinstance(foreign_key, str):
            self.foreign_key = foreign_key
        self.on_update = on_update
        self.on_delete = on_delete
        self.nullable = kwargs.pop("nullable", None)
        self.sa_column_extra = sa_column_extra or {}
        self.foreign_key_extra = foreign_key_extra or {}
        super().__init__(**kwargs)


class ReverseRelationshipField(RelationshipField):
    related_field: ForeignKeyField
    is_list: bool = False

    def __init__(
        self,
        related_field: Optional[str],
        on_update: Optional[str],
        on_delete: Optional[str],
        **kwargs: Any,
    ) -> None:
        if related_field is not None:
            self.related_field_name = related_field
        self.on_update = on_update
        self.on_delete = on_delete
        self.nullable = kwargs.pop("nullable", None)
        super().__init__(**kwargs)

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]


class ManyToManyField(RelationshipField):
    m2m_field_name: str
    m2m_table_field_name: str
    related_field: "ManyToManyField"
    table: Table
    sa_column_extra: Dict[str, Any]

    def __init__(
        self,
        related_field: Optional[str],
        many_to_many: Union[Literal[True], str],
        on_update: Optional[str],
        on_delete: Optional[str],
        sa_column_extra: Optional[Dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        if related_field is not None:
            self.related_field_name = related_field
        if isinstance(many_to_many, str):
            self.m2m_field_name = many_to_many
        self.on_update = on_update
        self.on_delete = on_delete
        self.sa_column_extra = sa_column_extra or {}
        self.nullable = kwargs.pop("nullable", None)
        super().__init__(**kwargs)


def Field(
    default: Any = Undefined,
    *,
    primary_key: bool = False,
    autoincrement: bool = False,
    index: bool = False,
    unique: bool = False,
    nullable: Optional[bool] = None,
    sa_column: Optional[Column] = None,
    sa_column_extra: Optional[Dict[str, Any]] = None,
    long_text: bool = False,
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
    if primary_key:
        nullable = False
    field_info = BaseField(
        default=default,
        default_factory=default_factory,
        primary_key=primary_key,
        autoincrement=autoincrement,
        index=index,
        unique=unique,
        nullable=nullable,
        sa_column=sa_column,
        sa_column_extra=sa_column_extra,
        long_text=long_text,
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
    related_field: Optional[str] = None,
    *,
    foreign_key: Union[Literal[True], str, None] = None,
    foreign_key_extra: Optional[Dict[str, Any]] = None,
    reverse_related: Optional[Literal[True]] = None,
    many_to_many: Union[Literal[True], str, None] = None,
    on_update: Optional[CASCADE_TYPE] = None,
    on_delete: Optional[CASCADE_TYPE] = None,
    nullable: Optional[bool] = None,
    sa_column_extra: Optional[Dict[str, Any]] = None,
    default: Any = Undefined,
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
    if sum(arg is not None for arg in (foreign_key, reverse_related, many_to_many)) > 1:
        raise ValueError(
            "Can only set foreign_key, reverse_related or many_to_many in one field",
        )
    if foreign_key is not None:
        field_info = ForeignKeyField(
            foreign_key=foreign_key,
            foreign_key_extra=foreign_key_extra,
            related_field=related_field,
            on_update=on_update,
            on_delete=on_delete,
            default=default,
            default_factory=default_factory,
            nullable=nullable,
            sa_column_extra=sa_column_extra,
            alias=alias,
            title=title,
            description=description,
            exclude=exclude,
            include=include,
            discriminator=discriminator,
            repr=repr,
            **extra,
        )
    elif many_to_many is not None:
        field_info = ManyToManyField(
            many_to_many=many_to_many,
            related_field=related_field,
            on_update=on_update,
            on_delete=on_delete,
            default=default,
            default_factory=default_factory,
            nullable=nullable,
            sa_column_extra=sa_column_extra,
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
        field_info = ReverseRelationshipField(
            related_field=related_field,
            on_update=on_update,
            on_delete=on_delete,
            nullable=nullable,
            default=default,
            default_factory=default_factory,
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
