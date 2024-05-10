from dataclasses import dataclass, field
from typing import Any, cast, TypedDict

from cherry.database import Database
from cherry.fields.fields import (
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)

from .index import CompositeIndex

from khemia.utils import classproperty
from pydantic import ConfigDict
from sqlalchemy import Column, MetaData, Table
from sqlalchemy.sql.schema import ColumnCollectionConstraint


class CherryConfig(TypedDict, total=False):
    tablename: str
    database: Database
    abstract: bool
    constraints: list[ColumnCollectionConstraint]
    indexes: list[CompositeIndex]
    use_jsonb_in_postgres: bool
    use_array_in_postgres: bool


@dataclass
class CherryMeta:
    tablename: str
    database: Database = field(init=False)
    table: Table = field(init=False)
    metadata: MetaData = field(init=False)
    abstract: bool = False
    constraints: list[ColumnCollectionConstraint] = field(default_factory=list)
    indexes: list[CompositeIndex] = field(default_factory=list)
    use_jsonb_in_postgres: bool = True
    use_array_in_postgres: bool = True
    columns: dict[str, Column] = field(default_factory=dict)
    primary_key: tuple[str, ...] = field(default_factory=tuple)
    related_fields: dict[str, ForeignKeyField] = field(default_factory=dict)
    reverse_related_fields: dict[str, ReverseRelationshipField] = field(
        default_factory=dict,
    )
    foreign_keys: tuple[str, ...] = field(default_factory=tuple)
    many_to_many_fields: dict[str, ManyToManyField] = field(default_factory=dict)
    many_to_many_tables: dict[str, Table] = field(default_factory=dict)


cherry_config_keys = set(CherryConfig.__annotations__.keys())


default_pydantic_config = ConfigDict(
    validate_assignment=True,
    from_attributes=True,
    ignored_types=(classproperty,),
    ser_json_bytes="base64",
)

# def generate_pydantic_config(namespace: dict[str, Any]):
#     default_config = ConfigDict(
#         validate_assignment=True,
#         from_attributes=True,
#         ignored_types=(classproperty,),
#         ser_json_bytes="base64",
#     )
#     if pydantic_config := namespace.get("model_config"):
#         if not check_isinstance(pydantic_config, dict):
#             raise TypeError("model_config must be a dict")
#         default_config.update(pydantic_config)
#     namespace["model_config"] = default_config


def generate_cherry_config(
    bases: tuple[type[Any], ...],
    namespace: dict[str, Any],
    extra_kwargs: dict[str, Any],
):
    config_new = CherryConfig()
    for base in bases:
        if config := getattr(base, "cherry_config", None):
            config_new.update(config.copy())
    config_class_from_namespace = namespace.get("Meta")
    config_dict_from_namespace = namespace.get("cherry_config")
    if config_class_from_namespace and config_dict_from_namespace:
        raise ValueError("Cannot define both Meta and cherry_config")
    if config_dict_from_namespace and isinstance(config_dict_from_namespace, dict):
        config_from_namespace = config_dict_from_namespace
    elif not config_class_from_namespace:
        config_from_namespace = {}
    else:
        config_from_namespace = {
            k: getattr(config_class_from_namespace, k)
            for k in dir(config_class_from_namespace)
            if k in cherry_config_keys
        }

    config_new.update(cast(CherryConfig, config_from_namespace))

    for k in list(extra_kwargs.keys()):
        if k in cherry_config_keys:
            config_new[k] = extra_kwargs.pop(k)
    namespace["cherry_config"] = config_new
