from re import Pattern
from typing import Any, Callable, Literal, Optional, TYPE_CHECKING, Union
from typing_extensions import Self, Unpack

from cherry.typing import CASCADE_TYPE

from pydantic.aliases import AliasChoices, AliasPath
from pydantic.config import JsonDict
from pydantic.fields import (
    _EmptyKwargs,
    _Unset,
    Deprecated,
    Field as PydanticField,
    FieldInfo,
)
from pydantic.types import Discriminator
from pydantic_core import PydanticUndefined
from sqlalchemy import Column, Table

if TYPE_CHECKING:
    from cherry.models import Model


class CherryField(FieldInfo):
    @classmethod
    def from_pydantic_field_info(cls, field_info: FieldInfo) -> Self:
        new_kwargs: dict[str, Any] = field_info._attributes_set.copy()
        metadata = {}
        for x in field_info.metadata:
            if not isinstance(x, FieldInfo):
                metadata[type(x)] = x
        new_field_info = cls(**new_kwargs)
        new_field_info.metadata = list(metadata.values())
        return new_field_info


class BaseField(CherryField):
    primary_key: bool = False
    autoincrement: bool = False
    index: bool = False
    unique: bool = False
    sa_column: Optional[Column]
    sa_column_extra: dict[str, Any] = {}
    nullable: Optional[bool] = None
    long_text: bool = False

    # def __init__(self, default: Any = ..., **kwargs: Any) -> None:
    #     self.primary_key = kwargs.pop("primary_key", False)
    #     self.autoincrement = kwargs.pop("autoincrement", False)
    #     self.index = kwargs.pop("index", False)
    #     self.unique = kwargs.pop("unique", False)
    #     self.nullable = kwargs.pop("nullable", None)
    #     self.sa_column = kwargs.pop("sa_column", None)
    #     self.sa_column_extra = kwargs.pop("sa_column_extra", {}) or {}
    #     self.long_text = kwargs.pop("long_text", False)
    #     super().__init__(default=default, **kwargs)


class RelationshipField(CherryField):
    related_model: type["Model"]
    related_field_name: str
    related_field: Optional["RelationshipField"]
    on_update: Optional[str]
    on_delete: Optional[str]
    nullable: Optional[bool] = None


class ForeignKeyField(RelationshipField):
    related_field: Optional["ReverseRelationshipField"] = None
    related_field_name: Optional[str] = None
    foreign_key: str
    foreign_key_self_name: str
    sa_column_extra: dict[str, Any]
    foreign_key_extra: dict[str, Any]

    # def __init__(
    #     self,
    #     related_field: Optional[str],
    #     foreign_key: Union[Literal[True], str],
    #     foreign_key_extra: Optional[dict[str, Any]],
    #     on_update: Optional[str],
    #     on_delete: Optional[str],
    #     sa_column_extra: Optional[dict[str, Any]],
    #     **kwargs: Any,
    # ) -> None:
    #     self.related_field = None  #  generate when generate model column
    #     self.related_field_name = related_field
    #     if isinstance(foreign_key, str):
    #         self.foreign_key = foreign_key
    #     self.on_update = on_update
    #     self.on_delete = on_delete
    #     self.nullable = kwargs.pop("nullable", None)
    #     self.sa_column_extra = sa_column_extra or {}
    #     self.foreign_key_extra = foreign_key_extra or {}
    #     super().__init__(**kwargs)


class ReverseRelationshipField(RelationshipField):
    related_field: ForeignKeyField
    is_list: bool = False

    def __repr_args__(self):
        attrs = ((s, getattr(self, s)) for s in self.__dict__)
        return [(a, v) for a, v in attrs if v]


class ManyToManyField(RelationshipField):
    m2m_field_name: str
    m2m_table_field_name: str
    related_field: "ManyToManyField"
    table: Table
    sa_column_extra: dict[str, Any]


def Field(
    default: Any = PydanticUndefined,
    *,
    primary_key: bool = _Unset,
    autoincrement: bool = _Unset,
    index: bool = _Unset,
    unique: bool = _Unset,
    nullable: Optional[bool] = _Unset,
    sa_column: Optional[Column] = _Unset,
    sa_column_extra: Optional[dict[str, Any]] = _Unset,
    long_text: bool = _Unset,
    default_factory: Optional[Callable[[], Any]] = _Unset,
    alias: Optional[str] = _Unset,
    alias_priority: Optional[int] = _Unset,
    validation_alias: Union[str, AliasPath, AliasChoices, None] = _Unset,
    serialization_alias: Optional[str] = _Unset,
    title: Optional[str] = _Unset,
    description: Optional[str] = _Unset,
    examples: Optional[list[Any]] = _Unset,
    exclude: Optional[bool] = _Unset,
    discriminator: Union[str, Discriminator, None] = _Unset,
    deprecated: Union[Deprecated, str, bool, None] = _Unset,
    json_schema_extra: Union[JsonDict, Callable[[JsonDict], None], None] = _Unset,
    frozen: Optional[bool] = _Unset,
    validate_default: Optional[bool] = _Unset,
    repr: bool = _Unset,
    init: Optional[bool] = _Unset,
    init_var: Optional[bool] = _Unset,
    kw_only: Optional[bool] = _Unset,
    pattern: Union[str, Pattern[str], None] = _Unset,
    strict: Optional[bool] = _Unset,
    coerce_numbers_to_str: Optional[bool] = _Unset,
    gt: Optional[float] = _Unset,
    ge: Optional[float] = _Unset,
    lt: Optional[float] = _Unset,
    le: Optional[float] = _Unset,
    multiple_of: Optional[float] = _Unset,
    allow_inf_nan: Optional[bool] = _Unset,
    max_digits: Optional[int] = _Unset,
    decimal_places: Optional[int] = _Unset,
    min_length: Optional[int] = _Unset,
    max_length: Optional[int] = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any:
    if primary_key:
        nullable = False
    field_info = BaseField.from_pydantic_field_info(
        PydanticField(
            default,
            default_factory=default_factory,
            alias=alias,
            alias_priority=alias_priority,
            validation_alias=validation_alias,
            serialization_alias=serialization_alias,
            title=title,
            description=description,
            examples=examples,
            exclude=exclude,
            discriminator=discriminator,
            deprecated=deprecated,
            json_schema_extra=json_schema_extra,
            frozen=frozen,
            pattern=pattern,
            validate_default=validate_default,
            repr=repr,
            init=init,
            init_var=init_var,
            kw_only=kw_only,
            coerce_numbers_to_str=coerce_numbers_to_str,
            strict=strict,
            gt=gt,
            ge=ge,
            lt=lt,
            le=le,
            multiple_of=multiple_of,
            min_length=min_length,
            max_length=max_length,
            allow_inf_nan=allow_inf_nan,
            max_digits=max_digits,
            decimal_places=decimal_places,
            union_mode=union_mode,
            **extra,
        ),
    )
    if primary_key is not _Unset:
        field_info.primary_key = primary_key
    if autoincrement is not _Unset:
        field_info.autoincrement = autoincrement
    if index is not _Unset:
        field_info.index = index
    if unique is not _Unset:
        field_info.unique = unique
    if nullable is not _Unset:
        field_info.nullable = nullable
    if sa_column is not _Unset:
        field_info.sa_column = sa_column
    if sa_column_extra and sa_column_extra is not _Unset:
        field_info.sa_column_extra = sa_column_extra
    if long_text is not _Unset:
        field_info.long_text = long_text
    return field_info


def Relationship(
    related_field: Optional[str] = None,
    *,
    foreign_key: Union[Literal[True], str, None] = None,
    foreign_key_extra: Optional[dict[str, Any]] = None,
    reverse_related: Optional[Literal[True]] = None,
    many_to_many: Union[Literal[True], str, None] = None,
    on_update: Optional[CASCADE_TYPE] = None,
    on_delete: Optional[CASCADE_TYPE] = None,
    nullable: Optional[bool] = None,
    sa_column_extra: Optional[dict[str, Any]] = None,
    default: Any = _Unset,
    default_factory: Optional[Callable[[], Any]] = _Unset,
    alias: Optional[str] = _Unset,
    alias_priority: Optional[int] = _Unset,
    validation_alias: Union[str, AliasPath, AliasChoices, None] = _Unset,
    serialization_alias: Optional[str] = _Unset,
    title: Optional[str] = _Unset,
    description: Optional[str] = _Unset,
    examples: Optional[list[Any]] = _Unset,
    exclude: Optional[bool] = _Unset,
    discriminator: Union[str, Discriminator, None] = _Unset,
    deprecated: Union[Deprecated, str, bool, None] = _Unset,
    json_schema_extra: Union[JsonDict, Callable[[JsonDict], None], None] = _Unset,
    frozen: Optional[bool] = _Unset,
    validate_default: Optional[bool] = _Unset,
    repr: bool = _Unset,
    init: Optional[bool] = _Unset,
    init_var: Optional[bool] = _Unset,
    kw_only: Optional[bool] = _Unset,
    pattern: Union[str, Pattern[str], None] = _Unset,
    strict: Optional[bool] = _Unset,
    coerce_numbers_to_str: Optional[bool] = _Unset,
    gt: Optional[float] = _Unset,
    ge: Optional[float] = _Unset,
    lt: Optional[float] = _Unset,
    le: Optional[float] = _Unset,
    multiple_of: Optional[float] = _Unset,
    allow_inf_nan: Optional[bool] = _Unset,
    max_digits: Optional[int] = _Unset,
    decimal_places: Optional[int] = _Unset,
    min_length: Optional[int] = _Unset,
    max_length: Optional[int] = _Unset,
    union_mode: Literal["smart", "left_to_right"] = _Unset,
    **extra: Unpack[_EmptyKwargs],
) -> Any:
    if sum(arg is not None for arg in (foreign_key, reverse_related, many_to_many)) > 1:
        raise ValueError(
            "Can only set foreign_key, reverse_related or many_to_many in one field",
        )
    pydantic_field_info = PydanticField(
        default,
        default_factory=default_factory,
        alias=alias,
        alias_priority=alias_priority,
        validation_alias=validation_alias,
        serialization_alias=serialization_alias,
        title=title,
        description=description,
        examples=examples,
        exclude=exclude,
        discriminator=discriminator,
        deprecated=deprecated,
        json_schema_extra=json_schema_extra,
        frozen=frozen,
        pattern=pattern,
        validate_default=validate_default,
        repr=repr,
        init=init,
        init_var=init_var,
        kw_only=kw_only,
        coerce_numbers_to_str=coerce_numbers_to_str,
        strict=strict,
        gt=gt,
        ge=ge,
        lt=lt,
        le=le,
        multiple_of=multiple_of,
        min_length=min_length,
        max_length=max_length,
        allow_inf_nan=allow_inf_nan,
        max_digits=max_digits,
        decimal_places=decimal_places,
        union_mode=union_mode,
        **extra,
    )
    if foreign_key:
        field_info = ForeignKeyField.from_pydantic_field_info(pydantic_field_info)
        if isinstance(foreign_key, str):
            field_info.foreign_key = foreign_key
        field_info.foreign_key_extra = foreign_key_extra or {}
        field_info.sa_column_extra = sa_column_extra or {}
    elif many_to_many:
        field_info = ManyToManyField.from_pydantic_field_info(pydantic_field_info)
        if related_field is not None:
            field_info.related_field_name = related_field
        if isinstance(many_to_many, str):
            field_info.m2m_table_field_name = many_to_many
        field_info.sa_column_extra = sa_column_extra or {}
    else:
        field_info = ReverseRelationshipField.from_pydantic_field_info(
            pydantic_field_info,
        )
        if related_field is not None:
            field_info.related_field_name = related_field
    field_info.on_update = on_update
    field_info.on_delete = on_delete
    field_info.nullable = nullable
    return field_info
