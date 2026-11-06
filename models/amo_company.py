# models/amo_company.py
from sqlalchemy import Column, BigInteger, String
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AmoCompany(db.Model):
    __tablename__ = "amo_company"

    id = Column(BigInteger, primary_key=True)  # ID компании в amoCRM
    name = Column(String, nullable=False, index=True)
    inn = Column(String, index=True)
    api_value = Column(JSONB)

    abstract_customer = db.relationship(
        "AbstractCustomer",
        back_populates="amo_companies",
        secondary="abstract_customer_company",
    )
