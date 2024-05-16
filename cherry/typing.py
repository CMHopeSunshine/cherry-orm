from collections.abc import Mapping
from typing import (
    Any,
    Literal,
    TYPE_CHECKING,
    TypeVar,
    Union,
)
from typing_extensions import TypeAlias, TypeVarTuple

from sqlalchemy import BinaryExpression, BooleanClauseList

if TYPE_CHECKING:
    from cherry.fields.proxy import ModelClause
    from cherry.models import Model

CASCADE_TYPE: TypeAlias = Literal[
    "RESTRICT",
    "CASCADE",
    "SET NULL",
    "NO ACTION",
    "SET DEFAULT",
]

CASCADE: Literal["CASCADE"] = "CASCADE"
RESTRICT: Literal["RESTRICT"] = "RESTRICT"
SET_NULL: Literal["SET NULL"] = "SET NULL"
NO_ACTION: Literal["NO ACTION"] = "NO ACTION"
SET_DEFAULT: Literal["SET DEFAULT"] = "SET DEFAULT"

T = TypeVar("T")
Ts = TypeVarTuple("Ts")
T_MODEL = TypeVar("T_MODEL", bound="Model")

ModelType = type["Model"]
DictStrAny: TypeAlias = dict[str, Any]
TupleAny: TypeAlias = tuple[Any, ...]
AnyMapping: TypeAlias = Mapping[Any, Any]
ClauseListType: TypeAlias = list[Union[BinaryExpression[bool], "ModelClause"]]
OptionalClause: TypeAlias = Union[BooleanClauseList, BinaryExpression, None]
