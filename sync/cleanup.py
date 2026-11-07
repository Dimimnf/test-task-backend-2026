from DAL import (
    AbstractCustomerDAL,
    AmoCompanyDAL,
    AmoContactDAL,
    AmoCustomerDAL,
    AmoLeadDAL,
)
from models.base import db
from sync.state import SyncState


def cleanup_stale_records(state: SyncState) -> None:
    """Атомарно удаляет сущности, которых нет в успешной выгрузке."""
    try:
        AbstractCustomerDAL.delete_not_in_ids(state.abstract_customer_ids)
        AmoCustomerDAL.delete_not_in_ids(state.customer_ids)
        AmoLeadDAL.delete_not_in_ids(state.lead_ids)
        AmoCompanyDAL.delete_not_in_ids(state.company_ids)
        AmoContactDAL.delete_not_in_ids(state.contact_ids)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
