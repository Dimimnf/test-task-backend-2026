from typing import Optional

from models.abstract_customer import AbstractCustomer
from models.amo_customer import AmoCustomer
from models.amo_lead import AmoLead
from models.base import db

from DAL.base_dal import BaseDAL


class AbstractCustomerDAL(BaseDAL):
    """DAO для агрегированных записей покупателей."""

    model = AbstractCustomer

    @classmethod
    def get_unique_by_customer_login(
        cls, login: str
    ) -> Optional[AbstractCustomer]:
        """Возвращает агрегат по логину CRM-покупателя, если он единственный."""
        stmt = (
            db.select(AbstractCustomer)
            .join(
                AmoCustomer,
                AmoCustomer.abstract_customer_id == AbstractCustomer.id,
            )
            .where(AmoCustomer.login == login)
            .distinct()
            .limit(2)
        )
        matches = db.session.execute(stmt).scalars().all()
        return matches[0] if len(matches) == 1 else None

    @classmethod
    def get_unique_by_lead_login(cls, login: str) -> Optional[AbstractCustomer]:
        """Возвращает агрегат по логину CRM-сделки, если он единственный."""
        stmt = (
            db.select(AbstractCustomer)
            .join(AmoLead, AmoLead.abstract_customer_id == AbstractCustomer.id)
            .where(AmoLead.login == login)
            .distinct()
            .limit(2)
        )
        matches = db.session.execute(stmt).scalars().all()
        return matches[0] if len(matches) == 1 else None
