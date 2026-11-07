from copy import deepcopy
import tracemalloc

from models import AmoCustomer
from sync.batch_writer import SyncBatchWriter
from sync.state import SyncState


def main():
    """Измеряет ID-наборы и один синтетический пакет sync writer."""
    tracemalloc.start()
    state = SyncState()
    state.customer_ids.update(range(1, 20_001))
    state.lead_ids.update(range(20_001, 70_001))
    state.abstract_customer_ids.update(range(70_001, 140_001))
    state_bytes = tracemalloc.get_traced_memory()[0]

    writer = SyncBatchWriter(batch_size=501)
    sample_api_value = {
        "id": 1,
        "name": "Customer",
        "status_id": 123,
        "custom_fields_values": [{"field_id": 1, "values": [{"value": "sample-login"}]}],
        "_embedded": {"contacts": [], "companies": []},
    }
    for customer_id in range(1, 501):
        writer.upsert(
            AmoCustomer,
            customer_id,
            {
                "abstract_customer_id": customer_id,
                "login": "sample-login",
                "name": "Customer",
                "api_value": deepcopy(sample_api_value),
            },
        )
    combined_bytes = tracemalloc.get_traced_memory()[0]

    print("state_ids_bytes=%d" % state_bytes)
    print("writer_500_rows_bytes=%d" % (combined_bytes - state_bytes))
    print("state_plus_writer_bytes=%d" % combined_bytes)


if __name__ == "__main__":
    main()
