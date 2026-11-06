from sync.cleanup import cleanup_stale_records
from sync.collector import collect_customers, collect_leads
from sync.state import SyncState


def collect_leads_customers(is_full: bool = True) -> None:
    """Запускает этапы CRM-синхронизации и очистку после полного прохода."""
    state = SyncState()
    collect_customers(state, is_full)
    collect_leads(state, is_full)

    if is_full:
        cleanup_stale_records(state)
