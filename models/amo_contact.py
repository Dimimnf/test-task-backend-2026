# models/amo_contact.py
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AmoContact(db.Model):
    __tablename__ = "amo_contact"

    id = Column(BigInteger, primary_key=True)  # ID контакта в amoCRM
    name = Column(String, nullable=False)
    phone = Column(String, index=True)
    api_value = Column(JSONB)

    abstract_customer = db.relationship(
        "AbstractCustomer",
        back_populates="amo_contacts",
        secondary="abstract_customer_contact",
    )
