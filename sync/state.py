from dataclasses import dataclass, field
from typing import Set


@dataclass
class SyncState:
    """ID агрегатов и CRM-сущностей, встреченных в текущей выгрузке."""

    abstract_customer_ids: Set[int] = field(default_factory=set)
    customer_ids: Set[int] = field(default_factory=set)
    lead_ids: Set[int] = field(default_factory=set)
    company_ids: Set[int] = field(default_factory=set)
    contact_ids: Set[int] = field(default_factory=set)
