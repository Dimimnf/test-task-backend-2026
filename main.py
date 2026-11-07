from sync.cleanup import cleanup_stale_records
from sync.collector import collect_customers, collect_leads
from sync.state import SyncState
from sync.batch_writer import SyncBatchWriter


def collect_leads_customers(is_full: bool = True) -> None:
    """Запускает этапы CRM-синхронизации и очистку после полного прохода."""
    state = SyncState()
    writer = SyncBatchWriter(batch_size=500)
    try:
        collect_customers(state, is_full, writer)
        writer.commit_pending()
        collect_leads(state, is_full, writer)
        writer.commit_pending()
    except Exception:
        writer.rollback()
        raise

    if is_full:
        cleanup_stale_records(state)
