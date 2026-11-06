from enum import Enum

from sqlalchemy import Column, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AbcCustomerEntities(Enum):
    AmoCustomer = 'amo_customers'
    AmoLead = 'amo_leads'
    AmoCompany = 'amo_companies'
    AmoContact = 'amo_contacts'
    SendMethods = 'send_methods'


class AbstractCustomer(db.Model):
    """
    "default" "general" : {
        "id": int
    }

    "amo_customers": [
        {
            "general": {
                "login": str,
                "billing_type": str,
                "is_robot": bool,
                "is_nds": bool,
                "system": str,
                "host": str,
                "name": str
            },
            "api_value": {}
        }
    ]

    "amo_leads": [
        {
            "general": {
                "login": Optional[str],
                "name": str
            }
            "api_value": {}
        }
    ]

    "amo_companies": [
        {
            "general": {
                "id": int,
                "inn": Optional[str],
                "name": str
            }
            "api_value": {}
        }
    ]

    "amo_contacts": [
        {
            "general": {
                "id": int,
                "phone": Optional[str],
                "name": str
            }
            "api_value": {}
        }
    ]

    "send_methods": [
        {
            "type": str (mail,sms,wtsp),
            "value": str,
            "desc": str,
        }
    ]
    """
    __tablename__ = "abstract_customer"
    id = Column(db.BigInteger(), nullable=False, primary_key=True)
    amo_customers = Column(JSONB)
    amo_leads = Column(JSONB)
    amo_companies = Column(JSONB)
    amo_contacts = Column(JSONB)
    send_methods = Column(JSONB)
    created_at = Column(db.DateTime, server_default=func.now())
    updated_at = Column(db.DateTime, onupdate=func.now())
