from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.infrastructure.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Base repository with infrastructure-only persistence helpers."""

    model_class: type[ModelT]

    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, model: ModelT) -> ModelT:
        self.db.add(model)
        return model

    def get(self, model_id: int) -> ModelT | None:
        return self.db.get(self.model_class, model_id)

    def flush(self) -> None:
        self.db.flush()
