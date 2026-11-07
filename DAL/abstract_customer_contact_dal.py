from sqlalchemy.dialects.postgresql import insert

from models.abstract_customer_contact import AbstractCustomerContact
from models.base import db

from DAL.base_dal import BaseDAL


class AbstractCustomerContactDAL(BaseDAL):
    """DAO связей между агрегатами покупателей и CRM-контактами."""

    model = AbstractCustomerContact

    @classmethod
    def attach(cls, abstract_customer_id: int, contact_id: int) -> None:
        """Создаёт связь агрегата с контактом, если её ещё нет."""
        link = cls.get_one_by(
            abstract_customer_id=abstract_customer_id,
            amo_contact_id=contact_id,
        )
        if link is None:
            cls.create(
                abstract_customer_id=abstract_customer_id,
                amo_contact_id=contact_id,
            )

    @classmethod
    def move_all(cls, source_id: int, target_id: int) -> None:
        """Переносит связи контактов с исходного агрегата на целевой."""
        if source_id == target_id:
            return

        table = cls.model.__table__
        statement = insert(table).from_select(
            ["abstract_customer_id", "amo_contact_id"],
            db.select(
                target_id,
                table.c.amo_contact_id,
            ).where(table.c.abstract_customer_id == source_id),
        ).on_conflict_do_nothing()
        db.session.execute(statement)
        db.session.execute(
            db.delete(cls.model).where(cls.model.abstract_customer_id == source_id)
        )
