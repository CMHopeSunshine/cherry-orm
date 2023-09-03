from typing import Any, Dict, Optional, Tuple, Type, TYPE_CHECKING
from typing_extensions import Annotated

from cherry.fields.annotated import FieldInfoEnum

import pydantic
from pydantic.fields import ModelField
from pydantic.typing import get_args, get_origin

if TYPE_CHECKING:
    from cherry.models.models import Model


def check_is_list(type_: Type[Any]) -> bool:
    ori = get_origin(type_)
    return ori is list


def get_annotated_field_info(type_: Type[Any]) -> Tuple[FieldInfoEnum, ...]:
    if get_origin(type_) is not Annotated:
        return ()
    return tuple(arg for arg in get_args(type_) if isinstance(arg, FieldInfoEnum))


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


def add_fields(model: Type["Model"], *field_definitions: Tuple[str, Type, Any]) -> None:
    """动态添加字段

    来源见: https://github.com/pydantic/pydantic/issues/1937
    """
    new_fields: Dict[str, ModelField] = {}
    new_annotations: Dict[str, Optional[Type]] = {}

    for f_def in field_definitions:
        f_name, f_annotation, f_value = f_def

        if f_annotation:
            new_annotations[f_name] = f_annotation

        new_fields[f_name] = ModelField.infer(
            name=f_name,
            value=f_value,
            annotation=f_annotation,
            class_validators=None,
            config=model.__config__,
        )

    model.__fields__.update(new_fields)
    model.__annotations__.update(new_annotations)
