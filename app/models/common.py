"""Shared domain-model configuration."""

from pydantic import BaseModel, ConfigDict


class DomainModel(BaseModel):
    """Base class that rejects unknown fields and validates assignments."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )
