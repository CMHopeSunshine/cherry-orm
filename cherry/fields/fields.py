from typing import Any, Dict, Literal, Optional, Type, TYPE_CHECKING, TypeVar, Union
from typing_extensions import Annotated, Self

from pydantic.fields import FieldInfo, Undefined
from pydantic.typing import NoArgAnyCallable
from sqlalchemy import Column

if TYPE_CHECKING:
    from cherry.models import Model

    from pydantic.typing import AbstractSetIntStr, MappingIntStrAny

T = TypeVar("T")

PrimaryKey = Annotated[T, "primary_key"]


class BaseField(FieldInfo):
    nullable: bool = False

    def __init__(self, default: Any = ..., **kwargs: Any) -> None:
        self.primary_key: bool = kwargs.pop("primary_key", False)
        self.autoincrement: bool = kwargs.pop("autoincrement", False)
        self.index: bool = kwargs.pop("index", False)
        self.column_type: Optional[Column] = kwargs.pop("column_type", None)
        self.unique: bool = kwargs.pop("unique", False)
        self.sa_column_args: Dict[str, Any] = kwargs.pop("sa_column_args", {}) or {}
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


class ForeignKeyField(FieldInfo):
    related_model: Type["Model"]
    foreign_key: str  #  example: "id"
    foreign_key_self_name: str  # example: "user_id"
    related_field_name: Optional[str]  # example: "user"
    related_field: Optional["ReverseRelationshipField"]

    def __init__(
        self,
        related_field: Optional[str],
        foreign_key: Union[Literal[True], str],
        **kwargs: Any,
    ) -> None:
        self.related_field = None  #  generate when generate model column
        # if related_field is not None:
        self.related_field_name = related_field
        if isinstance(foreign_key, str):
            self.foreign_key = foreign_key
        self.nullable: bool = kwargs.pop("nullable", False)
        super().__init__(**kwargs)


class ReverseRelationshipField(FieldInfo):
    related_model: Type["Model"]
    related_field_name: str
    related_field: ForeignKeyField
    is_list: bool

    def __init__(self, related_field: Optional[str], **kwargs: Any) -> None:
        if related_field is not None:
            self.related_field_name = related_field
        self.nullable: bool = kwargs.pop("nullable", False)
        super().__init__(**kwargs)

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]


class ManyToManyField(FieldInfo):
    many_to_many_key: str
    related_field_name: str
    related_field: "ManyToManyField"

    def __init__(
        self,
        related_field: Optional[str],
        many_to_many: Union[Literal[True], str],
        **kwargs: Any,
    ) -> None:
        if related_field is not None:
            self.related_field_name = related_field
        if isinstance(many_to_many, str):
            self.many_to_many_key = many_to_many
        self.nullable: bool = kwargs.pop("nullable", False)
        super().__init__(**kwargs)


def Field(
    default: Any = Undefined,
    *,
    primary_key: bool = False,
    autoincrement: bool = False,
    index: bool = False,
    column_type: Optional[Column] = None,
    unique: bool = False,
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
    field_info = BaseField(
        default=default,
        default_factory=default_factory,
        primary_key=primary_key,
        autoincrement=autoincrement,
        index=index,
        column_type=column_type,
        unique=unique,
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
    related_field: Optional[str] = None,
    *,
    foreign_key: Union[Literal[True], str, None] = None,
    reverse_related: Optional[Literal[True]] = None,
    many_to_many: Union[Literal[True], str, None] = None,
    sa_column_args: Optional[Dict[str, Any]] = None,
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
            related_field=related_field,
            # others will be save in extra
            reverse_related=reverse_related,
            many_to_many=many_to_many,
            default=default,
            default_factory=default_factory,
            sa_column_args=sa_column_args,
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
            # others will be save in extra
            foreign_key=foreign_key,
            reverse_related=reverse_related,
            default=default,
            default_factory=default_factory,
            sa_column_args=sa_column_args,
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
            # others will be save in extra
            foreign_key=foreign_key,
            reverse_related=reverse_related,
            many_to_many=many_to_many,
            default=default,
            default_factory=default_factory,
            sa_column_args=sa_column_args,
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
