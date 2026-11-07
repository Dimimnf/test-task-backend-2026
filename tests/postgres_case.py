import os
import unittest

from flask import Flask
from sqlalchemy import text

from models import db


class PostgresCase(unittest.TestCase):
    """Базовый case с отдельной схемой в тестовой PostgreSQL."""

    @classmethod
    def setUpClass(cls):
        database_url = os.environ.get("TEST_DATABASE_URL")
        if not database_url:
            raise unittest.SkipTest("задайте TEST_DATABASE_URL для PostgreSQL-тестов")

        cls.app = Flask(__name__)
        cls.app.config.update(
            SQLALCHEMY_DATABASE_URI=database_url,
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(cls.app)
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        if not os.environ.get("TEST_DATABASE_USE_MIGRATION"):
            db.drop_all()
            db.create_all()

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "app_context"):
            db.session.remove()
            cls.app_context.pop()

    def setUp(self):
        if os.environ.get("TEST_DATABASE_USE_MIGRATION"):
            db.session.execute(
                text(
                    "TRUNCATE TABLE abstract_customer_company, "
                    "abstract_customer_contact, amo_customer, amo_lead, "
                    "amo_company, amo_contact, abstract_customer "
                    "RESTART IDENTITY CASCADE"
                )
            )
            db.session.commit()
        else:
            db.drop_all()
            db.create_all()

    def tearDown(self):
        db.session.rollback()


def customer_record(customer_id, login, name="Customer"):
    """Создаёт CRM-покупателя с минимально полным набором полей API."""

    class CustomerRecord:
        def __init__(self):
            self.id = customer_id
            self.name = name
            self.next_price = self.next_date = None
            self.responsible_user_id = self.status_id = self.periodicity = None
            self.created_by = self.updated_by = self.created_at = self.updated_at = None
            self.closest_task_at = self.is_deleted = self.ltv = self.purchases_count = None
            self.average_check = self.account_id = None
            self.custom_fields_values = self._embedded = None
            self.companies = []
            self.contacts = []

        def get_field(self, field_name):
            return login if field_name == "Логин" else None

    return CustomerRecord()
