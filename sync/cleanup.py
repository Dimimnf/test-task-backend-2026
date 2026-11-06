from DAL import (
    AbstractCustomerDAL,
    AmoCompanyDAL,
    AmoContactDAL,
    AmoCustomerDAL,
    AmoLeadDAL,
)
from sync.state import SyncState


def cleanup_stale_records(state: SyncState) -> None:
    """Удаляет агрегаты и CRM-сущности, которых нет в выгрузке."""
    AbstractCustomerDAL.delete_not_in_ids(state.abstract_customer_ids)
    AmoCustomerDAL.delete_not_in_ids(state.customer_ids)
    AmoLeadDAL.delete_not_in_ids(state.lead_ids)
    AmoCompanyDAL.delete_not_in_ids(state.company_ids)
    AmoContactDAL.delete_not_in_ids(state.contact_ids)
