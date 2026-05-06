from pydantic import BaseModel, field_validator

from Domain.ExternalProvider import ExternalProvider


class ProvidersConfig(BaseModel):
    external_providers: list[ExternalProvider]

    @field_validator("external_providers")
    @classmethod
    def must_not_be_empty(cls, v: list[ExternalProvider]):
        if not v:
            raise ValueError("At least one external provider must be configured")
        return v