import abc
import operator
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Mapping,
    Tuple,
    Type,
    TYPE_CHECKING,
    Union,
)
from typing_extensions import Self

from cherry.exception import FieldTypeError
from cherry.typing import ModelType

from .fields import (
    ForeignKeyField,
    ManyToManyField,
    ReverseRelationshipField,
)
from .utils import create_nested_dict

from pydantic import BaseModel
from sqlalchemy import BinaryExpression, Column, ColumnElement, JSON

if TYPE_CHECKING:
    from cherry.models import Model


OperatorFunc = Callable[[Any, Any], ColumnElement[bool]]


class ModelClauseBase(abc.ABC):
    @property
    @abc.abstractmethod
    def binary_expression(self) -> ColumnElement[bool]:
        raise NotImplementedError

    def __and__(self, other: "Union[ModelClauseBase, BinaryExpression]"):
        if isinstance(other, ModelClauseBase):
            return self.binary_expression & other.binary_expression
        return self.binary_expression & other

    def __or__(self, other: "Union[ModelClauseBase, BinaryExpression]"):
        if isinstance(other, ModelClauseBase):
            return self.binary_expression | other.binary_expression
        return self.binary_expression | other


class ModelClause(ModelClauseBase):
    def __init__(
        self,
        model_cls: Type["Model"],
        value: Any,
        field_name: str,
        field: Union[ForeignKeyField, ReverseRelationshipField, ManyToManyField],
        op: OperatorFunc = operator.eq,
    ) -> None:
        if isinstance(field, ForeignKeyField) or (
            isinstance(field, ReverseRelationshipField) and not field.is_list
        ):
            self.model_cls = model_cls
            self.value = value
            self.field = field
            self.field_name = field_name
            self.op = op
        else:
            raise FieldTypeError(f"cannnot use equal operator on {type(field)}")

    @property
    def binary_expression(self) -> ColumnElement[bool]:
        if isinstance(self.field, ForeignKeyField):
            return self.op(
                getattr(
                    self.model_cls,
                    self.field.foreign_key_self_name,
                ),
                (
                    getattr(
                        self.value,
                        self.field.foreign_key,
                    )
                    if isinstance(self.value, self.field.related_model)
                    else self.value
                ),
            )
        else:
            if isinstance(self.value, self.field.related_model):
                return self.value.get_pk_filter()
            else:
                return self.op(
                    getattr(
                        self.field.related_model,
                        self.field.related_field_name,
                    ),
                    self.value,
                )

    def __repr__(self) -> str:
        return f"{self.model_cls.__name__}.{self.field_name} {self.op.__name__} {self.value}"  # noqa: E501


class RelatedModelProxy:
    def __init__(
        self,
        self_model: ModelType,
        related_model: ModelType,
        field_name: str,
        field: Union[ForeignKeyField, ReverseRelationshipField, ManyToManyField],
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

    def __ne__(self, other: "Model") -> ModelClause:
        return ModelClause(self.model, other, self.field_name, self.field, operator.ne)

    def get_column(self) -> Column:
        if not isinstance(self.field, ForeignKeyField):
            raise FieldTypeError(
                (
                    "cannot use unique constraint on"
                    f" {self.field_name}:{self.field.__class__.__name__}"
                ),
            )
        return getattr(self.model, self.field.foreign_key_self_name)


class JsonFieldClause(ModelClauseBase):
    def __init__(
        self,
        ce: ColumnElement[JSON],
        value: Any,
        path: List[str],
        op: OperatorFunc = operator.eq,
    ) -> None:
        self.ce = ce
        self.value = value
        self.path = path
        self.op = op

    def get_value(self) -> Any:
        if not self.path:
            return self.value
        return create_nested_dict(self.path, self.value)

    @property
    def binary_expression(self) -> ColumnElement[bool]:
        return self.op(self.ce, self.value)

    def __repr__(self) -> str:
        return f"{self.ce} {self.op.__name__} {self.value}"


def conversion_type(
    ce: ColumnElement[JSON],
    value: Any,
) -> Tuple[ColumnElement[JSON], Any]:
    if isinstance(value, str):
        return ce.as_string(), value
    if isinstance(value, int):
        return ce.as_integer(), value
    if isinstance(value, float):
        return ce.as_float(), value
    if isinstance(value, bool):
        return ce.as_boolean(), value
    if isinstance(value, BaseModel):
        return ce.as_json(), value.dict()
    if isinstance(value, (Iterable, Mapping)):
        return ce.as_json(), value
    return ce, value


class JsonFieldPathProxy:
    def __init__(
        self,
        column: Column,
        path: List[str],
    ) -> None:
        self.column: Column[JSON] = column
        self.path = path

    def __getitem__(self, key: str) -> Self:
        self.path.append(key)
        return self

    def __getattr__(self, name: str) -> Self:
        self.path.append(name)
        return self

    def __eq__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.eq,
        )

    def __ne__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.ne,
        )

    def __ge__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.ge,
        )

    def __gt__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.gt,
        )

    def __le__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.le,
        )

    def __lt__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(
            *conversion_type(
                self.column[self.path if len(self.path) == 1 else tuple(self.path)],
                other,
            ),
            self.path,
            operator.lt,
        )


class JsonFieldProxy:
    def __init__(
        self,
        column: Column,
    ) -> None:
        self.column: Column[JSON] = column

    def __getitem__(self, key: str) -> JsonFieldPathProxy:
        return JsonFieldPathProxy(self.column, [key])

    def __getattr__(self, name: str) -> JsonFieldPathProxy:
        return JsonFieldPathProxy(self.column, [name])

    def __eq__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.eq)

    def __ne__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.ne)

    def __ge__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.ge)

    def __gt__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.gt)

    def __le__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.le)

    def __lt__(self, other: object) -> JsonFieldClause:
        return JsonFieldClause(*conversion_type(self.column, other), [], operator.lt)
