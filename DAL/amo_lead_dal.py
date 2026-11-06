from typing import Optional

from models.amo_lead import AmoLead
from models.base import db

from DAL.base_dal import BaseDAL


class AmoLeadDAL(BaseDAL):
    """DAO для CRM-сделок."""

    model = AmoLead

    @classmethod
    def get_unique_by_login(cls, login: str) -> Optional[AmoLead]:
        """Возвращает сделку по логину, только если совпадение одно."""
        stmt = db.select(cls.model).where(cls.model.login == login).limit(2)
        matches = db.session.execute(stmt).scalars().all()
        return matches[0] if len(matches) == 1 else None
