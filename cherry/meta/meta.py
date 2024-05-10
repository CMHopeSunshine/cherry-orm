from typing import (
    Any,
    ClassVar,
    Optional,
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
    columns: ClassVar[dict[str, Column]]
    constraints: ClassVar[list[ColumnCollectionConstraint]]
    indexes: ClassVar[list[CompositeIndex]]
    abstract: ClassVar[bool]
    primary_key: ClassVar[tuple[str, ...]]
    related_fields: ClassVar[dict[str, ForeignKeyField]]
    reverse_related_fields: ClassVar[dict[str, ReverseRelationshipField]]
    foreign_keys: ClassVar[tuple[str, ...]]
    many_to_many_fields: ClassVar[dict[str, ManyToManyField]]
    many_to_many_tables: ClassVar[dict[str, Table]]
    use_jsonb_in_postgres: ClassVar[bool]
    use_array_in_postgres: ClassVar[bool]


def mix_meta_config(
    self_config: Optional[type[MetaConfig]],
    parent_config: type[MetaConfig],
    **namespace: Any,
) -> type[MetaConfig]:
    if not self_config:
        base_classes = (parent_config,)
    elif self_config == parent_config:
        base_classes = (self_config,)
    else:
        base_classes = self_config, parent_config

    return type("Meta", base_classes, namespace)


def init_meta_config(
    meta_config: type[MetaConfig],
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
    meta_config.use_jsonb_in_postgres = True
    meta_config.use_array_in_postgres = True
