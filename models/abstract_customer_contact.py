from sqlalchemy import BigInteger, Column, ForeignKey

from models.base import db


class AbstractCustomerContact(db.Model):
    """Связь между агрегатом покупателя и CRM-контактом."""

    __tablename__ = "abstract_customer_contact"

    abstract_customer_id = Column(
        BigInteger,
        ForeignKey("abstract_customer.id", ondelete="CASCADE"),
        primary_key=True,
    )
    amo_contact_id = Column(
        BigInteger,
        ForeignKey("amo_contact.id", ondelete="CASCADE"),
        primary_key=True,
    )
