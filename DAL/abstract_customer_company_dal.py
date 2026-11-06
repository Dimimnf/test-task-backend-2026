from typing import Set

from models.abstract_customer_company import AbstractCustomerCompany
from models.base import db

from DAL.base_dal import BaseDAL


class AbstractCustomerCompanyDAL(BaseDAL):
    """DAO связей между агрегатами покупателей и CRM-компаниями."""

    model = AbstractCustomerCompany

    @classmethod
    def attach(cls, abstract_customer_id: int, company_id: int) -> None:
        """Создаёт связь агрегата с компанией, если её ещё нет."""
        link = cls.get_one_by(
            abstract_customer_id=abstract_customer_id,
            amo_company_id=company_id,
        )
        if link is None:
            cls.create(
                abstract_customer_id=abstract_customer_id,
                amo_company_id=company_id,
            )

    @classmethod
    def move_all(cls, source_id: int, target_id: int) -> None:
        """Переносит связи компаний с исходного агрегата на целевой."""
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
                    db.select(cls.model.amo_company_id).where(
                        cls.model.abstract_customer_id == target_id
                    )
                ).scalars().all()
            )
            for link in source_links:
                if link.amo_company_id not in target_ids:
                    db.session.add(
                        cls.model(
                            abstract_customer_id=target_id,
                            amo_company_id=link.amo_company_id,
                        )
                    )
                    target_ids.add(link.amo_company_id)
                db.session.delete(link)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
