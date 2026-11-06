from typing import Optional, Tuple

from DAL import AbstractCustomerDAL, AmoCustomerDAL, AmoLeadDAL
from models import AbstractCustomer, AmoCustomer, AmoLead


def find_customer_match(
    customer_id: int,
    login: str,
) -> Tuple[Optional[AmoCustomer], Optional[AbstractCustomer]]:
    """Возвращает CRM-покупателя и его агрегат либо агрегат по логину сделок."""
    customer = AmoCustomerDAL.get_by_id(customer_id)
    if customer is not None:
        return customer, customer.abstract_customer
    aggregate = AbstractCustomerDAL.get_unique_by_lead_login(login) if login else None
    return None, aggregate


def find_lead_aggregates(
    lead_id: int,
    login: Optional[str],
) -> Tuple[Optional[AmoLead], Optional[AbstractCustomer], Optional[AbstractCustomer]]:
    """Возвращает сделку и агрегаты по ID сделки и логину покупателя."""
    lead = AmoLeadDAL.get_by_id(lead_id)
    lead_aggregate = lead.abstract_customer if lead is not None else None
    customer_aggregate = (
        AbstractCustomerDAL.get_unique_by_customer_login(login)
        if login
        else None
    )
    return lead, lead_aggregate, customer_aggregate
