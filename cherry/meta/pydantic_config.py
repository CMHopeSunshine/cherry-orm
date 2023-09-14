import inspect
from typing import Any

from cherry.fields.utils import classproperty

from pydantic import BaseConfig


def get_default_pydantic_config():
    class PydanticBaseConfig(BaseConfig):
        orm_mode = True
        validate_assignment = True
        keep_untouched = (classproperty,)

    return PydanticBaseConfig


def generate_pydantic_config(attrs: dict[str, Any]):
    default_config = get_default_pydantic_config()
    if (config := attrs.get("Config")) and inspect.isclass(config):
        new_config = type("Config", (default_config, config), {})
        attrs["Config"] = new_config
    else:
        attrs["Config"] = default_config
