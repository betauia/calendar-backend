# Domain/service_result.py
from typing import Generic, TypeVar
from pydantic import BaseModel
from enum import Enum

T = TypeVar("T")

class ErrorCode(Enum):
    NONE = "none"
    NOT_FOUND = "not_found"
    CONNECTION_ERROR = "connection_error"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "unknown"

class ServiceResult(BaseModel, Generic[T]):
    is_successful: bool
    value: T | None = None
    error_code: ErrorCode = ErrorCode.NONE
    error_description: str | None = None

    @staticmethod
    def success(value: T | None = None) -> "ServiceResult[T]":
        return ServiceResult(is_successful=True, value=value)

    @staticmethod
    def failure(error_code: ErrorCode, error_description: str) -> "ServiceResult[T]":
        return ServiceResult(
            is_successful=False,
            error_code=error_code,
            error_description=error_description
        )