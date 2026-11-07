from sqlalchemy.dialects.postgresql import insert

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

        table = cls.model.__table__
        statement = insert(table).from_select(
            ["abstract_customer_id", "amo_company_id"],
            db.select(
                target_id,
                table.c.amo_company_id,
            ).where(table.c.abstract_customer_id == source_id),
        ).on_conflict_do_nothing()
        db.session.execute(statement)
        db.session.execute(
            db.delete(cls.model).where(cls.model.abstract_customer_id == source_id)
        )
