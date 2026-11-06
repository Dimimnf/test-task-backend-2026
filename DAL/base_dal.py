from typing import Any, ClassVar, Optional, Type

from sqlalchemy import inspect

from models.base import db


class BaseDAL:
    """Базовый DAL для операций с одной SQLAlchemy-моделью."""

    model: ClassVar[Optional[Type[Any]]] = None



    @classmethod
    def get_by_id(cls, entity_id: Any) -> Optional[Any]:
        """Ищет запись по первичному ключу."""
        return db.session.get(cls.model, entity_id)

    @classmethod
    def get_one_by(cls, **filters: Any) -> Optional[Any]:
        """Ищет одну запись по значениям атрибутов модели."""
        model = cls.model
        stmt = db.select(model).filter_by(**filters)
        return db.session.execute(stmt).scalar_one_or_none()

    @classmethod
    def create(cls, **values: Any) -> Any:
        """Создаёт объект модели и фиксирует его в базе данных."""
        model = cls.model
        entity = model(**values)
        try:
            db.session.add(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return entity

    @classmethod
    def update_by_id(cls, entity_id: Any, **values: Any) -> Optional[Any]:
        """Обновляет поля записи по первичному ключу."""
        entity = cls.get_by_id(entity_id)
        if entity is None:
            return None

        allowed_fields = {column.key for column in inspect(cls.model).columns}
        unknown_fields = values.keys() - allowed_fields
        if unknown_fields:
            names = ", ".join(sorted(unknown_fields))
            raise ValueError(f"Неизвестные поля модели: {names}")

        try:
            for field, value in values.items():
                setattr(entity, field, value)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return entity

    @classmethod
    def delete_by_id(cls, entity_id: Any) -> bool:
        """Удаляет запись по первичному ключу; возвращает признак удаления."""
        entity = cls.get_by_id(entity_id)
        if entity is None:
            return False

        try:
            db.session.delete(entity)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return True
