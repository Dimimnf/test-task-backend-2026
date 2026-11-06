from sqlalchemy import BigInteger, Column, ForeignKey

from models.base import db


class AbstractCustomerCompany(db.Model):
    """Связь между агрегатом покупателя и CRM-компанией."""

    __tablename__ = "abstract_customer_company"

    abstract_customer_id = Column(
        BigInteger,
        ForeignKey("abstract_customer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    amo_company_id = Column(
        BigInteger,
        ForeignKey("amo_company.id", ondelete="CASCADE"),
        primary_key=True,
    )
