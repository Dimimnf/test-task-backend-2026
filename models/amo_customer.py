# models/amo_customer.py
from sqlalchemy import Column, BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AmoCustomer(db.Model):
    __tablename__ = "amo_customer"

    id = Column(BigInteger, primary_key=True)  # ID покупателя в amoCRM
    abstract_customer_id = Column(
        BigInteger,
        ForeignKey("abstract_customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    login = Column(String, index=True)
    name = Column(String, nullable=False)
    api_value = Column(JSONB)