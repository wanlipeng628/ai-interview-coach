from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard response envelope reserved for business APIs."""

    code: str = "SUCCESS"
    message: str = "success"
    data: T | None = None
