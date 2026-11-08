from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    """База схем API: в JSON поля в camelCase (как привычно фронту), в Python — snake_case."""

    model_config = ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)
