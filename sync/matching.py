from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from models import AbstractCustomer, AmoCustomer, AmoLead, db


@dataclass
class MatchCache:
    """Пакетный индекс совпадений для одной страницы CRM."""

    customers_by_id: Dict[int, AmoCustomer] = field(default_factory=dict)
    leads_by_id: Dict[int, AmoLead] = field(default_factory=dict)
    aggregate_by_lead_login: Dict[str, AbstractCustomer] = field(default_factory=dict)
    aggregate_by_customer_login: Dict[str, AbstractCustomer] = field(default_factory=dict)

    def add_customer(self, customer: AmoCustomer) -> None:
        """Добавляет покупателя в текущий индекс."""
        self.customers_by_id[customer.id] = customer

    def add_lead(self, lead: AmoLead) -> None:
        """Добавляет сделку в текущий индекс."""
        self.leads_by_id[lead.id] = lead


def _aggregates_by_login(model, login_values: Iterable[str]) -> Dict[str, AbstractCustomer]:
    """Загружает агрегаты только для логинов с единственным совпадением."""
    values = {value for value in login_values if value}
    if not values:
        return {}
    grouped = db.session.execute(
        db.select(
            model.login,
            func.min(model.abstract_customer_id).label("aggregate_id"),
            func.count(func.distinct(model.abstract_customer_id)).label("matches"),
        )
        .where(model.login.in_(values))
        .group_by(model.login)
    ).all()
    unique_ids = {
        row.aggregate_id for row in grouped if row.matches == 1
    }
    if not unique_ids:
        return {}
    aggregates = db.session.execute(
        db.select(AbstractCustomer).where(AbstractCustomer.id.in_(unique_ids))
    ).scalars()
    aggregates_by_id = {aggregate.id: aggregate for aggregate in aggregates}
    return {
        row.login: aggregates_by_id[row.aggregate_id]
        for row in grouped
        if row.matches == 1 and row.aggregate_id in aggregates_by_id
    }


def prefetch_customer_matches(customers: Iterable[object]) -> MatchCache:
    """Пакетно загружает покупателей по ID и агрегаты по логинам сделок."""
    records = list(customers)
    cache = MatchCache()
    ids = {record.id for record in records}
    if ids:
        for customer in db.session.execute(
            db.select(AmoCustomer)
            .options(joinedload(AmoCustomer.abstract_customer))
            .where(AmoCustomer.id.in_(ids))
        ).scalars():
            cache.add_customer(customer)
    cache.aggregate_by_lead_login = _aggregates_by_login(
        AmoLead, (record.get_field("Логин") for record in records)
    )
    return cache


def prefetch_lead_matches(leads: Iterable[object]) -> MatchCache:
    """Пакетно загружает сделки по ID и агрегаты по логинам покупателей."""
    records = list(leads)
    cache = MatchCache()
    ids = {record.id for record in records}
    if ids:
        for lead in db.session.execute(
            db.select(AmoLead)
            .options(joinedload(AmoLead.abstract_customer))
            .where(AmoLead.id.in_(ids))
        ).scalars():
            cache.add_lead(lead)
    cache.aggregate_by_customer_login = _aggregates_by_login(
        AmoCustomer, (record.get_field("Логин") for record in records)
    )
    return cache


def find_customer_match(
    customer_id: int,
    login: str,
    cache: MatchCache,
) -> Tuple[Optional[AmoCustomer], Optional[AbstractCustomer]]:
    """Возвращает CRM-покупателя и его агрегат либо агрегат по логину сделок."""
    customer = cache.customers_by_id.get(customer_id)
    if customer is not None:
        return customer, customer.abstract_customer
    return None, cache.aggregate_by_lead_login.get(login)


def find_lead_aggregates(
    lead_id: int,
    login: Optional[str],
    cache: MatchCache,
) -> Tuple[Optional[AmoLead], Optional[AbstractCustomer], Optional[AbstractCustomer]]:
    """Возвращает сделку и агрегаты по ID сделки и логину покупателя."""
    lead = cache.leads_by_id.get(lead_id)
    lead_aggregate = lead.abstract_customer if lead is not None else None
    return lead, lead_aggregate, cache.aggregate_by_customer_login.get(login)
