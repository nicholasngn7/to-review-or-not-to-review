"""Shared Pydantic base for the review contract.

Every model in the contract serializes to and accepts camelCase JSON so the API
matches the TypeScript types used by the frontend, while keeping idiomatic
snake_case field names in Python.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model that maps snake_case fields to camelCase JSON keys.

    `populate_by_name` lets callers construct models with either the Python
    field name or the camelCase alias. FastAPI serializes responses with
    `by_alias=True` by default, so responses come out camelCase automatically.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )
