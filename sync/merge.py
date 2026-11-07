from sqlalchemy import delete, update

from DAL import AbstractCustomerCompanyDAL, AbstractCustomerContactDAL
from models import AbstractCustomer, AmoCustomer, AmoLead, db


def merge_abstract_customers(
    target: AbstractCustomer,
    source: AbstractCustomer,
) -> AbstractCustomer:
    """Переносит сущности в целевой агрегат и удаляет исходный."""
    if target.id == source.id:
        return target

    try:
        db.session.execute(
            update(AmoCustomer)
            .where(AmoCustomer.abstract_customer_id == source.id)
            .values(abstract_customer_id=target.id)
        )
        db.session.execute(
            update(AmoLead)
            .where(AmoLead.abstract_customer_id == source.id)
            .values(abstract_customer_id=target.id)
        )

        AbstractCustomerContactDAL.move_all(source.id, target.id)
        AbstractCustomerCompanyDAL.move_all(source.id, target.id)
        db.session.execute(delete(AbstractCustomer).where(AbstractCustomer.id == source.id))
        db.session.expire_all()
    except Exception:
        db.session.rollback()
        raise
    return target
