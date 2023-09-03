from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)

from cherry.database import Database
from cherry.fields.fields import BaseField, ForeignKeyField, RelationshipField

from sqlalchemy import Column, MetaData, Table
from sqlalchemy.sql.schema import ColumnCollectionConstraint

if TYPE_CHECKING:
    pass


class MetaConfig:
    tablename: ClassVar[str]
    database: ClassVar[Database]
    table: ClassVar[Table]
    metadata: ClassVar[MetaData]
    columns: ClassVar[Dict[str, Column]]
    constraints: ClassVar[List[ColumnCollectionConstraint]]
    abstract: ClassVar[bool]
    model_fields: ClassVar[
        Dict[str, Union[BaseField, RelationshipField, ForeignKeyField]]
    ]
    primary_key: ClassVar[Tuple[str, ...]]
    related_fields: ClassVar[Dict[str, ForeignKeyField]]
    back_related_fields: ClassVar[Dict[str, RelationshipField]]
    foreign_keys: ClassVar[Tuple[str, ...]]


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
    meta_config.model_fields = {}
    meta_config.columns = {}
    meta_config.constraints = []
    meta_config.related_fields = {}
    meta_config.back_related_fields = {}
