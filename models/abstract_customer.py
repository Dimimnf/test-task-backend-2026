from sqlalchemy import Column, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from models.base import db


class AbstractCustomer(db.Model):
    __tablename__ = "abstract_customer"

    id = Column(BigInteger, primary_key=True, nullable=False)

    # Todo: понять нужно ли это в jsonb
    send_methods = Column(JSONB)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Обратные ORM-связи. Имена классов дочерних моделей
    # SQLAlchemy найдёт по строке при регистрации моделей.
    amo_customers = db.relationship(
        "AmoCustomer",
        back_populates="abstract_customer",
        cascade="all, delete-orphan",
    )
    amo_leads = db.relationship(
        "AmoLead",
        back_populates="abstract_customer",
        cascade="all, delete-orphan",
    )
    amo_companies = db.relationship(
        "AmoCompany",
        back_populates="abstract_customer",
        cascade="all, delete-orphan",
    )
    amo_contacts = db.relationship(
        "AmoContact",
        back_populates="abstract_customer",
        cascade="all, delete-orphan",
    )