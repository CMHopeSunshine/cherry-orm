from typing import Type, TYPE_CHECKING

from cherry.exception import FieldTypeError
from cherry.typing import ModelType

from .fields import ForeignKeyField, RelationshipField, ReverseRelationshipField

from sqlalchemy import ColumnElement

if TYPE_CHECKING:
    from cherry.models import Model


class ModelClause:
    def __init__(
        self,
        model_cls: Type["Model"],
        model: "Model",
        field_name: str,
        field: RelationshipField,
    ) -> None:
        if isinstance(field, ForeignKeyField) or (
            isinstance(field, ReverseRelationshipField) and not field.is_list
        ):
            self.model_cls = model_cls
            self.model = model
            self.field = field
            self.field_name = field_name
        else:
            raise FieldTypeError(f"cannnot use equal operator on {type(field)}")

    @property
    def binary_expression(self) -> ColumnElement[bool]:
        if isinstance(self.field, ForeignKeyField):
            return getattr(
                self.model_cls,
                self.field.foreign_key_self_name,
            ) == getattr(
                self.model,
                self.field.foreign_key,
            )
        else:
            return self.model.get_pk_filter()

    def __repr__(self) -> str:
        return f"{self.model_cls.__name__}.{self.field_name} == {self.model}"


class RelatedModelProxy:
    def __init__(
        self,
        self_model: ModelType,
        related_model: ModelType,
        field_name: str,
        field: RelationshipField,
    ):
        self.model = self_model
        self.related_model = related_model
        self.field_name = field_name
        self.field = field

    def __getattr__(self, name: str):
        return getattr(self.related_model, name)

    def __repr__(self) -> str:
        return f"{self.model}.{self.related_model}"

    def __eq__(self, other: "Model") -> ModelClause:
        return ModelClause(self.model, other, self.field_name, self.field)
