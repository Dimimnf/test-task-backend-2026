from typing import Optional

from models.amo_customer import AmoCustomer
from models.base import db

from DAL.base_dal import BaseDAL


class AmoCustomerDAL(BaseDAL):
    """DAO для CRM-покупателей."""

    model = AmoCustomer

    @classmethod
    def get_unique_by_login(cls, login: str) -> Optional[AmoCustomer]:
        """Возвращает покупателя по логину, только если совпадение одно."""
        stmt = db.select(cls.model).where(cls.model.login == login).limit(2)
        matches = db.session.execute(stmt).scalars().all()
        return matches[0] if len(matches) == 1 else None
