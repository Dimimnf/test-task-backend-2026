import logging
from typing import Any, Dict, Iterable, Optional, Set

from amocrm import COMPANIES, CONTACTS, Customer, Lead, amocrm_get
from DAL import (
    AbstractCustomerCompanyDAL,
    AbstractCustomerContactDAL,
    AbstractCustomerDAL,
    AmoCompanyDAL,
    AmoContactDAL,
    AmoCustomerDAL,
    AmoLeadDAL,
)
from sync.matching import find_customer_match, find_lead_aggregates
from sync.merge import merge_abstract_customers
from sync.state import SyncState

logger = logging.getLogger(__name__)
DELETE_MARKER = "удалить"


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
    extra_values: Optional[Dict[str, Any]] = None,
    skip_marked: bool = True,
) -> None:
    """Сохраняет встроенную компанию или контакт и связь с агрегатом."""
    entity_id = data.get("id")
    name = data.get("name") or ""
    if entity_id is None or (skip_marked and _is_marked_for_deletion(name)):
        return

    values = {"name": name, "api_value": data, **(extra_values or {})}
    entity = dao.get_by_id(entity_id)
    if entity is None:
        dao.create(id=entity_id, **values)
    else:
        dao.update_by_id(entity_id, **values)

    link_dal.attach(aggregate_id, entity_id)
    state_ids.add(entity_id)


def process_customer(
    customer: Customer,
    state: SyncState,
    is_full: bool,
) -> Optional[int]:
    """Сохраняет покупателя и вложенные сущности; возвращает ID агрегата."""
    login = customer.get_field("Логин")
    if not login or (is_full and _is_marked_for_deletion(customer.name)):
        return None

    amo_customer, aggregate = find_customer_match(customer.id, login)
    if aggregate is None:
        aggregate = AbstractCustomerDAL.create()

    values = {
        "abstract_customer_id": aggregate.id,
        "login": login,
        "name": customer.name,
        "api_value": _customer_api_value(customer),
    }
    if amo_customer is None:
        AmoCustomerDAL.create(id=customer.id, **values)
    else:
        AmoCustomerDAL.update_by_id(customer.id, **values)

    state.customer_ids.add(customer.id)
    state.abstract_customer_ids.add(aggregate.id)

    for company in _embedded_items(customer, COMPANIES):
        _upsert_related_entity(
            AmoCompanyDAL,
            AbstractCustomerCompanyDAL,
            aggregate.id,
            company,
            state.company_ids,
            {"inn": company.get("inn")},
            skip_marked=is_full,
        )
    for contact in _embedded_items(customer, CONTACTS):
        _upsert_related_entity(
            AmoContactDAL,
            AbstractCustomerContactDAL,
            aggregate.id,
            contact,
            state.contact_ids,
            {"phone": contact.get("phone")},
            skip_marked=is_full,
        )

    return aggregate.id


def process_lead(
    lead: Lead,
    state: SyncState,
    is_full: bool,
) -> Optional[int]:
    """Сохраняет сделку и контакты; возвращает ID её агрегата."""
    if is_full and _is_marked_for_deletion(lead.name):
        return None

    amo_lead, aggregate, customer_aggregate = find_lead_aggregates(
        lead.id,
        lead.get_field("Логин"),
    )
    if aggregate is None:
        aggregate = customer_aggregate
    elif (
        customer_aggregate is not None
        and customer_aggregate.id != aggregate.id
    ):
        aggregate = merge_abstract_customers(aggregate, customer_aggregate)

    if aggregate is None:
        aggregate = AbstractCustomerDAL.create()

    values = {
        "abstract_customer_id": aggregate.id,
        "login": lead.get_field("Логин"),
        "name": lead.name or "",
        "api_value": _lead_api_value(lead),
    }
    if amo_lead is None:
        AmoLeadDAL.create(id=lead.id, **values)
    else:
        AmoLeadDAL.update_by_id(lead.id, **values)

    state.lead_ids.add(lead.id)
    state.abstract_customer_ids.add(aggregate.id)

    for contact in _embedded_items(lead, CONTACTS):
        _upsert_related_entity(
            AmoContactDAL,
            AbstractCustomerContactDAL,
            aggregate.id,
            contact,
            state.contact_ids,
            {"phone": contact.get("phone")},
            skip_marked=is_full,
        )

    return aggregate.id


def collect_customers(state: SyncState, is_full: bool) -> None:
    """Выгружает и сохраняет CRM-покупателей."""
    logger.info("Сбор покупателей amoCRM: is_full=%s", is_full)
    for customer in amocrm_get(Customer, _with=f"{COMPANIES},{CONTACTS}"):
        if not is_full and customer.status_id == 111349:
            continue
        process_customer(customer, state, is_full)


def collect_leads(state: SyncState, is_full: bool) -> None:
    """Выгружает и сохраняет CRM-сделки."""
    logger.info("Сбор сделок amoCRM: is_full=%s", is_full)
    for lead in amocrm_get(Lead, _with=CONTACTS):
        if not is_full and lead.status_id == 143:
            continue
        process_lead(lead, state, is_full)
