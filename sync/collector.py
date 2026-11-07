import logging
from typing import Any, Callable, Dict, Iterable, Optional, Set, Type

from amocrm import COMPANIES, CONTACTS, Customer, Lead, amocrm_get
from DAL import (
    AbstractCustomerCompanyDAL,
    AbstractCustomerContactDAL,
    AmoCompanyDAL,
    AmoContactDAL,
    AmoCustomerDAL,
    AmoLeadDAL,
)
from sync.batch_writer import SyncBatchWriter
from sync.matching import (
    MatchCache,
    find_customer_match,
    find_lead_aggregates,
    prefetch_customer_matches,
    prefetch_lead_matches,
)
from sync.merge import merge_abstract_customers
from sync.state import SyncState
from models.base import db

logger = logging.getLogger(__name__)
DELETE_MARKER = "удалить"

# Статусы, которые пропускаются при неполной синхронизации.
_CUSTOMER_SKIP_STATUS_ID = 111349
_LEAD_SKIP_STATUS_ID = 143


def _is_marked_for_deletion(name: Any) -> bool:
    """Проверяет маркер удаления в имени CRM-сущности."""
    return DELETE_MARKER in (name or "").lower()


def _embedded_items(entity: Any, key: str) -> Iterable[Dict[str, Any]]:
    """Возвращает встроенные записи из объекта или его _embedded-поля."""
    items = getattr(entity, key, None)
    if not items:
        items = (getattr(entity, "_embedded", None) or {}).get(key, [])
    if isinstance(items, dict):
        items = items.get("items", [items])
    return items or []


def _customer_api_value(customer: Customer) -> Dict[str, Any]:
    """Собирает явное представление покупателя amoCRM для хранения в JSONB."""
    return {
        "id": customer.id,
        "name": customer.name,
        "next_price": customer.next_price,
        "next_date": customer.next_date,
        "responsible_user_id": customer.responsible_user_id,
        "status_id": customer.status_id,
        "periodicity": customer.periodicity,
        "created_by": customer.created_by,
        "updated_by": customer.updated_by,
        "created_at": customer.created_at,
        "updated_at": customer.updated_at,
        "closest_task_at": customer.closest_task_at,
        "is_deleted": customer.is_deleted,
        "ltv": customer.ltv,
        "purchases_count": customer.purchases_count,
        "average_check": customer.average_check,
        "account_id": customer.account_id,
        "custom_fields_values": customer.custom_fields_values,
        "_embedded": customer._embedded,
    }


def _lead_api_value(lead: Lead) -> Dict[str, Any]:
    """Собирает явное представление сделки amoCRM для хранения в JSONB."""
    return {
        "id": lead.id,
        "name": lead.name,
        "price": lead.price,
        "responsible_user_id": lead.responsible_user_id,
        "group_id": lead.group_id,
        "status_id": lead.status_id,
        "pipeline_id": lead.pipeline_id,
        "source_id": lead.source_id,
        "created_by": lead.created_by,
        "updated_by": lead.updated_by,
        "created_at": lead.created_at,
        "updated_at": lead.updated_at,
        "closest_task_at": lead.closest_task_at,
        "is_deleted": lead.is_deleted,
        "score": lead.score,
        "account_id": lead.account_id,
        "custom_fields_values": lead.custom_fields_values,
        "_embedded": lead._embedded,
    }


def _upsert_related_entity(
    dao: Any,
    link_dal: Any,
    aggregate_id: int,
    data: Dict[str, Any],
    state_ids: Set[int],
    writer: SyncBatchWriter,
    extra_values: Optional[Dict[str, Any]] = None,
    skip_marked: bool = True,
) -> None:
    """Сохраняет встроенную компанию или контакт и связь с агрегатом."""
    entity_id = data.get("id")
    name = data.get("name") or ""
    if entity_id is None or (skip_marked and _is_marked_for_deletion(name)):
        return

    values = {"name": name, "api_value": data, **(extra_values or {})}
    writer.upsert(dao.model, entity_id, values)
    writer.attach(link_dal.model, (aggregate_id, entity_id))
    state_ids.add(entity_id)


def process_customer(
    customer: Customer,
    state: SyncState,
    is_full: bool,
    writer: SyncBatchWriter,
    match_cache: Optional[MatchCache] = None,
) -> Optional[int]:
    """Сохраняет покупателя и вложенные сущности; возвращает ID агрегата."""
    login = customer.get_field("Логин")
    if not login or (is_full and _is_marked_for_deletion(customer.name)):
        return None

    if match_cache is None:
        match_cache = prefetch_customer_matches([customer])

    with db.session.no_autoflush:
        amo_customer, aggregate = find_customer_match(customer.id, login, match_cache)
    if aggregate is None:
        aggregate = writer.new_aggregate()

    aggregate_id = aggregate.id
    writer.upsert(
        AmoCustomerDAL.model,
        customer.id,
        {
            "abstract_customer_id": aggregate_id,
            "login": login,
            "name": customer.name,
            "api_value": _customer_api_value(customer),
        },
    )

    state.customer_ids.add(customer.id)
    state.abstract_customer_ids.add(aggregate_id)

    for company in _embedded_items(customer, COMPANIES):
        _upsert_related_entity(
            AmoCompanyDAL,
            AbstractCustomerCompanyDAL,
            aggregate_id,
            company,
            state.company_ids,
            writer,
            {"inn": company.get("inn")},
            skip_marked=is_full,
        )
    for contact in _embedded_items(customer, CONTACTS):
        _upsert_related_entity(
            AmoContactDAL,
            AbstractCustomerContactDAL,
            aggregate_id,
            contact,
            state.contact_ids,
            writer,
            {"phone": contact.get("phone")},
            skip_marked=is_full,
        )

    return aggregate_id


def process_lead(
    lead: Lead,
    state: SyncState,
    is_full: bool,
    writer: SyncBatchWriter,
    match_cache: Optional[MatchCache] = None,
) -> Optional[int]:
    """Сохраняет сделку и контакты; возвращает ID её агрегата."""
    if is_full and _is_marked_for_deletion(lead.name):
        return None

    if match_cache is None:
        match_cache = prefetch_lead_matches([lead])

    with db.session.no_autoflush:
        amo_lead, aggregate, customer_aggregate = find_lead_aggregates(
            lead.id,
            lead.get_field("Логин"),
            match_cache,
        )
    if aggregate is None:
        aggregate = customer_aggregate
    elif (
        customer_aggregate is not None
        and customer_aggregate.id != aggregate.id
    ):
        writer.redirect_aggregate(customer_aggregate.id, aggregate.id)
        aggregate = merge_abstract_customers(aggregate, customer_aggregate)
        writer.generation += 1

    if aggregate is None:
        aggregate = writer.new_aggregate()

    aggregate_id = aggregate.id
    writer.upsert(
        AmoLeadDAL.model,
        lead.id,
        {
            "abstract_customer_id": aggregate_id,
            "login": lead.get_field("Логин"),
            "name": lead.name or "",
            "api_value": _lead_api_value(lead),
        },
    )

    state.lead_ids.add(lead.id)
    state.abstract_customer_ids.add(aggregate_id)

    for contact in _embedded_items(lead, CONTACTS):
        _upsert_related_entity(
            AmoContactDAL,
            AbstractCustomerContactDAL,
            aggregate_id,
            contact,
            state.contact_ids,
            writer,
            {"phone": contact.get("phone")},
            skip_marked=is_full,
        )

    return aggregate_id


def collect_customers(
    state: SyncState, is_full: bool, writer: SyncBatchWriter
) -> None:
    """Выгружает и сохраняет CRM-покупателей."""
    _collect_entities(
        label="покупателей",
        entity_cls=Customer,
        _with=f"{COMPANIES},{CONTACTS}",
        skip_status_id=_CUSTOMER_SKIP_STATUS_ID,
        process_fn=process_customer,
        prefetch_fn=prefetch_customer_matches,
        state=state,
        is_full=is_full,
        writer=writer,
    )


def collect_leads(
    state: SyncState, is_full: bool, writer: SyncBatchWriter
) -> None:
    """Выгружает и сохраняет CRM-сделки."""
    _collect_entities(
        label="сделок",
        entity_cls=Lead,
        _with=CONTACTS,
        skip_status_id=_LEAD_SKIP_STATUS_ID,
        process_fn=process_lead,
        prefetch_fn=prefetch_lead_matches,
        state=state,
        is_full=is_full,
        writer=writer,
    )


def _collect_entities(
    label: str,
    entity_cls: Type[Any],
    _with: str,
    skip_status_id: Optional[int],
    process_fn: Callable,
    prefetch_fn: Callable,
    state: SyncState,
    is_full: bool,
    writer: SyncBatchWriter,
) -> None:
    """Выгружает сущности amoCRM страницами и обрабатывает их батчами."""
    logger.info("Сбор %s amoCRM: is_full=%s", label, is_full)
    page: list = []
    for entity in amocrm_get(entity_cls, _with=_with):
        if not is_full and skip_status_id is not None and entity.status_id == skip_status_id:
            continue
        page.append(entity)
        if len(page) == 250:
            _process_page(page, state, is_full, writer, prefetch_fn, process_fn)
            page = []
    if page:
        _process_page(page, state, is_full, writer, prefetch_fn, process_fn)


def _process_page(
    page: list,
    state: SyncState,
    is_full: bool,
    writer: SyncBatchWriter,
    prefetch_fn: Callable,
    process_fn: Callable,
) -> None:
    """Обрабатывает ограниченное окно CRM-записей с пакетным поиском."""
    cache = prefetch_fn(page)
    generation = writer.generation
    for index, record in enumerate(page):
        if writer.generation != generation:
            cache = prefetch_fn(page[index:])
            generation = writer.generation
        process_fn(record, state, is_full, writer, cache)
