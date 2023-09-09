from typing import Any, Callable, Dict, Generic, Optional, Type, TYPE_CHECKING, TypeVar

import pydantic

T = TypeVar("T")


if TYPE_CHECKING:
    from cherry.models.models import Model


def validate_fields(
    model: Type["Model"],
    input_data: Dict[str, Any],
) -> Dict[str, Any]:
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
    """类属性装饰器"""

    def __init__(self, func: Callable[[Any], T]) -> None:
        self.func = func

    def __get__(self, instance: Any, owner: Optional[Type[Any]] = None) -> T:
        return self.func(type(instance) if owner is None else owner)
