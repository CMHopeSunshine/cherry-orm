from functools import reduce
from typing import Any, Callable, Generic, List, Optional, Type

from cherry.typing import ClauseListType, DictStrAny, ModelType, T, TupleAny

import pydantic
from sqlalchemy import Column
from sqlalchemy.sql import operators as sa_op

operator_mapping = {
    "is": sa_op.is_,
    "is_not": sa_op.is_not,
    "not": sa_op.ne,
    "gt": sa_op.gt,
    "ge": sa_op.ge,
    "gte": sa_op.ge,
    "lt": sa_op.lt,
    "le": sa_op.le,
    "lte": sa_op.le,
    "distinct_from": sa_op.is_distinct_from,
    "not_distinct_from": sa_op.is_not_distinct_from,
    "negative": sa_op.neg,
    "contains": sa_op.contains_op,
    "icontains": sa_op.icontains_op,
    "match": sa_op.match_op,
    "not_match": sa_op.not_match_op,
    "regexp_match": sa_op.regexp_match_op,
    "not_regexp_match": sa_op.not_regexp_match_op,
    "like": sa_op.like_op,
    "not_like": sa_op.not_like_op,
    "ilike": sa_op.ilike_op,
    "not_ilike": sa_op.not_ilike_op,
    "in": sa_op.in_op,
    "not_in": sa_op.not_in_op,
    "startswith": sa_op.startswith_op,
    "istartswith": sa_op.istartswith_op,
    "endswith": sa_op.endswith_op,
    "iendswith": sa_op.iendswith_op,
    "between": sa_op.between_op,
    "concat": sa_op.concat_op,
    "all": sa_op.all_op,
    "any": sa_op.any_op,
    "exists": sa_op.exists,
}


def args_and_kwargs_to_clause_list(
    model: ModelType,
    args: TupleAny,
    kwargs: DictStrAny,
) -> ClauseListType:
    column_elements = []
    for name, value in kwargs.items():
        attrs = name.split("__")
        if attrs[-1] in operator_mapping:
            operator = operator_mapping[attrs[-1]]
            attrs = attrs[:-1]
        else:
            operator = sa_op.eq
        attr: Column = reduce(
            lambda d, key: getattr(d, key),
            attrs,
            model,
        )
        column_elements.append(operator(attr, value))
    column_elements.extend(args)
    return column_elements


def validate_fields(
    model: ModelType,
    input_data: DictStrAny,
) -> DictStrAny:
    if miss := set(input_data) - set(model.__fields__):
        raise ValueError(f"{model.__name__} has no fields: {miss}")

    fields = {
        k: (v.outer_type_, v.field_info)
        for k, v in model.__fields__.items()
        if k in input_data
    }
    new_model = pydantic.create_model(model.__name__, **fields)  # type: ignore
    values, _, validation_error = pydantic.validate_model(new_model, input_data)

    if validation_error:
        raise validation_error

    return values


class classproperty(Generic[T]):
    def __init__(self, func: Callable[[Any], T]) -> None:
        self.func = func

    def __get__(self, instance: Any, owner: Optional[Type[Any]] = None) -> T:
        return self.func(type(instance) if owner is None else owner)


def create_nested_dict(path: List[str], value: Any):
    if len(path) == 1:
        return {path[0]: value}
    else:
        return {path[0]: create_nested_dict(path[1:], value)}
