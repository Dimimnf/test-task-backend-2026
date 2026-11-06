# models/amo_contact.py
from sqlalchemy import Column, BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AmoContact(db.Model):
    __tablename__ = "amo_contact"

    id = Column(BigInteger, primary_key=True)  # ID контакта в amoCRM
    abstract_customer_id = Column(
        BigInteger,
        ForeignKey("abstract_customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False)
    phone = Column(String, index=True)
    api_value = Column(JSONB)