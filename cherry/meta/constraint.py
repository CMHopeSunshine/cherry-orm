from typing import Any, Optional

from cherry.exception import FieldTypeError
from cherry.fields import ManyToManyField, ReverseRelationshipField
from cherry.fields.proxy import RelatedModelProxy


def Unique(*fields: Any, name: Optional[str] = None):
    for field in fields:
        if isinstance(field, RelatedModelProxy):
            if isinstance(field.field, (ReverseRelationshipField, ManyToManyField)):
                raise FieldTypeError(
                    (
                        "cannot use unique constraint on"
                        f" {field.field_name}:{field.field.__class__.__name__}"
                    ),
                )
            else:
                raw_field = getattr(
                    field.model,
                    field.field.foreign_key_self_name,
                )
