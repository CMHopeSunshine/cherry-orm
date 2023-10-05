from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
)

from cherry.database import Database
from cherry.fields.fields import (
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)

from .index import CompositeIndex

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.sql.schema import ColumnCollectionConstraint


class MetaConfig:
    tablename: ClassVar[str]
    database: ClassVar[Database]
    table: ClassVar[Table]
    metadata: ClassVar[MetaData]
    columns: ClassVar[Dict[str, Column]]
    constraints: ClassVar[List[ColumnCollectionConstraint]]
    indexes: ClassVar[List[CompositeIndex]]
    abstract: ClassVar[bool]
    primary_key: ClassVar[Tuple[str, ...]]
    related_fields: ClassVar[Dict[str, ForeignKeyField]]
    reverse_related_fields: ClassVar[Dict[str, ReverseRelationshipField]]
    foreign_keys: ClassVar[Tuple[str, ...]]
    many_to_many_fields: ClassVar[Dict[str, ManyToManyField]]
    many_to_many_tables: ClassVar[Dict[str, Table]]


def mix_meta_config(
    self_config: Optional[Type[MetaConfig]],
    parent_config: Type[MetaConfig],
    **namespace: Any,
) -> Type[MetaConfig]:
    if not self_config:
        base_classes = (parent_config,)
    elif self_config == parent_config:
        base_classes = (self_config,)
    else:
        base_classes = self_config, parent_config

    return type("Meta", base_classes, namespace)


def init_meta_config(
    meta_config: Type[MetaConfig],
):
    if not hasattr(meta_config, "abstract"):
        meta_config.abstract = False
    meta_config.columns = {}
    meta_config.constraints = []
    meta_config.related_fields = {}
    meta_config.reverse_related_fields = {}
    meta_config.many_to_many_fields = {}
    meta_config.many_to_many_tables = {}
    meta_config.indexes = []
