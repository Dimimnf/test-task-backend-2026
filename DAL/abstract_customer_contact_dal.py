from typing import Set

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

        try:
            source_links = db.session.execute(
                db.select(cls.model).where(
                    cls.model.abstract_customer_id == source_id
                )
            ).scalars().all()
            target_ids: Set[int] = set(
                db.session.execute(
                    db.select(cls.model.amo_contact_id).where(
                        cls.model.abstract_customer_id == target_id
                    )
                ).scalars().all()
            )
            for link in source_links:
                if link.amo_contact_id not in target_ids:
                    db.session.add(
                        cls.model(
                            abstract_customer_id=target_id,
                            amo_contact_id=link.amo_contact_id,
                        )
                    )
                    target_ids.add(link.amo_contact_id)
                db.session.delete(link)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
