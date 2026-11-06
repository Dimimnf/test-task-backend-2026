from models import AbstractCustomer, db
from DAL import AbstractCustomerCompanyDAL, AbstractCustomerContactDAL


def merge_abstract_customers(
    target: AbstractCustomer,
    source: AbstractCustomer,
) -> AbstractCustomer:
    """Переносит сущности в целевой агрегат и удаляет исходный."""
    if target.id == source.id:
        return target

    try:
        for entity in list(source.amo_customers) + list(source.amo_leads):
            entity.abstract_customer = target

        AbstractCustomerContactDAL.move_all(source.id, target.id)
        AbstractCustomerCompanyDAL.move_all(source.id, target.id)

        db.session.flush()
        db.session.delete(source)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return target
