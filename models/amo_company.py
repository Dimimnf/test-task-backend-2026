# models/amo_company.py
from sqlalchemy import Column, BigInteger, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AmoCompany(db.Model):
    __tablename__ = "amo_company"

    id = Column(BigInteger, primary_key=True)  # ID компании в amoCRM
    abstract_customer_id = Column(
        BigInteger,
        ForeignKey("abstract_customer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String, nullable=False, index=True)
    inn = Column(String, index=True)
    api_value = Column(JSONB)