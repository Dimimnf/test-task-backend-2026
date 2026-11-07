from unittest.mock import patch

from sqlalchemy import event, select

from DAL import AbstractCustomerDAL, AmoCompanyDAL, AmoCustomerDAL, AmoLeadDAL
from models import (
    AbstractCustomer,
    AbstractCustomerCompany,
    AmoCompany,
    AmoCustomer,
    AmoLead,
    db,
)
from sync.batch_writer import SyncBatchWriter
from sync.cleanup import cleanup_stale_records
from sync.collector import process_customer, process_lead
from sync.matching import prefetch_customer_matches, prefetch_lead_matches
from sync.state import SyncState
from tests.postgres_case import PostgresCase, customer_record


class PostgresSyncTests(PostgresCase):
    """Проверяет batch-операции и бизнес-правила на PostgreSQL."""

    def _aggregate(self):
        aggregate = AbstractCustomer()
        db.session.add(aggregate)
        db.session.flush()
        return aggregate

    def test_customer_without_login_is_skipped(self):
        state = SyncState()
        self.assertIsNone(
            process_customer(customer_record(101, None), state, True, SyncBatchWriter())
        )
        self.assertEqual(state.customer_ids, set())

    def test_delete_marker_is_skipped_only_during_full_sync(self):
        marked = customer_record(111, "marked-login", "удалить later")
        full_state = SyncState()
        self.assertIsNone(process_customer(marked, full_state, True, SyncBatchWriter()))

        partial_state = SyncState()
        writer = SyncBatchWriter(batch_size=20)
        process_customer(marked, partial_state, False, writer)
        writer.commit_pending()

        self.assertEqual(full_state.customer_ids, set())
        self.assertIn(111, partial_state.customer_ids)

    def test_customer_id_match_takes_precedence_over_login_match(self):
        id_match = self._aggregate()
        login_match = self._aggregate()
        db.session.add_all(
            [
                AmoCustomer(
                    id=101,
                    abstract_customer_id=id_match.id,
                    login="old-login",
                    name="Existing",
                ),
                AmoLead(
                    id=201,
                    abstract_customer_id=login_match.id,
                    login="new-login",
                    name="Lead",
                ),
            ]
        )
        db.session.commit()

        writer = SyncBatchWriter(batch_size=20)
        process_customer(customer_record(101, "new-login"), SyncState(), True, writer)
        writer.commit_pending()

        self.assertEqual(AmoCustomerDAL.get_by_id(101).abstract_customer_id, id_match.id)

    def test_customer_matches_unique_existing_lead_login(self):
        aggregate = self._aggregate()
        db.session.add(
            AmoLead(
                id=201,
                abstract_customer_id=aggregate.id,
                login="same-login",
                name="Lead",
            )
        )
        db.session.commit()

        state = SyncState()
        writer = SyncBatchWriter(batch_size=20)
        process_customer(customer_record(101, "same-login"), state, True, writer)
        writer.commit_pending()

        saved = AmoCustomerDAL.get_by_id(101)
        self.assertEqual(saved.abstract_customer_id, aggregate.id)

    def test_page_prefetch_uses_batch_queries_and_preserves_unique_login_rule(self):
        aggregate = self._aggregate()
        db.session.add_all(
            [
                AmoLead(
                    id=201,
                    abstract_customer_id=aggregate.id,
                    login="page-login",
                    name="Lead",
                ),
                AmoCustomer(
                    id=101,
                    abstract_customer_id=aggregate.id,
                    login="customer-login",
                    name="Customer",
                ),
            ]
        )
        db.session.commit()
        customers = [customer_record(999, "page-login")]
        leads = [
            type(
                "LeadRecord",
                (),
                {"id": 999, "get_field": lambda self, name: "customer-login"},
            )()
        ]
        statements = []

        def record_select(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", record_select)
        try:
            customer_cache = prefetch_customer_matches(customers)
            lead_cache = prefetch_lead_matches(leads)
        finally:
            event.remove(db.engine, "before_cursor_execute", record_select)

        self.assertEqual(len(statements), 6)
        self.assertIs(customer_cache.aggregate_by_lead_login["page-login"], aggregate)
        self.assertIs(lead_cache.aggregate_by_customer_login["customer-login"], aggregate)

    def test_ambiguous_lead_login_does_not_match_customer(self):
        first = self._aggregate()
        second = self._aggregate()
        db.session.add_all(
            [
                AmoLead(id=201, abstract_customer_id=first.id, login="dup", name="A"),
                AmoLead(id=202, abstract_customer_id=second.id, login="dup", name="B"),
            ]
        )
        db.session.commit()

        state = SyncState()
        writer = SyncBatchWriter(batch_size=20)
        process_customer(customer_record(101, "dup"), state, True, writer)
        writer.commit_pending()

        self.assertNotEqual(AmoCustomerDAL.get_by_id(101).abstract_customer_id, first.id)
        self.assertNotEqual(AmoCustomerDAL.get_by_id(101).abstract_customer_id, second.id)

    def test_ambiguous_customer_login_does_not_match_lead(self):
        first = self._aggregate()
        second = self._aggregate()
        db.session.add_all(
            [
                AmoCustomer(id=401, abstract_customer_id=first.id, login="dup", name="A"),
                AmoCustomer(id=402, abstract_customer_id=second.id, login="dup", name="B"),
            ]
        )
        db.session.commit()
        lead = type(
            "LeadRecord",
            (),
            {
                "id": 301,
                "name": "New",
                "price": None,
                "responsible_user_id": None,
                "group_id": None,
                "status_id": None,
                "pipeline_id": None,
                "source_id": None,
                "created_by": None,
                "updated_by": None,
                "created_at": None,
                "updated_at": None,
                "closest_task_at": None,
                "is_deleted": None,
                "score": None,
                "account_id": None,
                "custom_fields_values": None,
                "_embedded": None,
                "contacts": [],
                "get_field": lambda self, name: "dup" if name == "Логин" else None,
            },
        )()

        state = SyncState()
        writer = SyncBatchWriter(batch_size=20)
        process_lead(lead, state, True, writer)
        writer.commit_pending()

        saved = AmoLeadDAL.get_by_id(301)
        self.assertNotIn(saved.abstract_customer_id, {first.id, second.id})

    def test_lead_id_aggregate_wins_and_other_aggregate_is_merged(self):
        target = self._aggregate()
        source = self._aggregate()
        db.session.add_all(
            [
                AmoLead(id=301, abstract_customer_id=target.id, login="old", name="Existing"),
                AmoCustomer(id=401, abstract_customer_id=source.id, login="buyer-login", name="Buyer"),
                AmoCompany(id=501, name="Company"),
            ]
        )
        db.session.flush()
        db.session.add(
            AbstractCustomerCompany(
                abstract_customer_id=source.id,
                amo_company_id=501,
            )
        )
        db.session.commit()

        state = SyncState()
        writer = SyncBatchWriter(batch_size=100)
        writer.upsert(
            AmoLeadDAL.model,
            302,
            {
                "abstract_customer_id": source.id,
                "login": "pending-login",
                "name": "Pending",
                "api_value": None,
            },
        )
        writer.attach(AbstractCustomerCompany, (source.id, 501))
        lead = type(
            "LeadRecord",
            (),
            {
                "id": 301,
                "name": "Updated",
                "price": None,
                "responsible_user_id": None,
                "group_id": None,
                "status_id": None,
                "pipeline_id": None,
                "source_id": None,
                "created_by": None,
                "updated_by": None,
                "created_at": None,
                "updated_at": None,
                "closest_task_at": None,
                "is_deleted": None,
                "score": None,
                "account_id": None,
                "custom_fields_values": None,
                "_embedded": None,
                "contacts": [],
                "get_field": lambda self, name: "buyer-login" if name == "Логин" else None,
            },
        )()
        session = db.session()
        commits = []

        def record_commit(current):
            commits.append(1)

        event.listen(session, "after_commit", record_commit)
        process_lead(lead, state, True, writer)
        self.assertEqual(commits, [])
        writer.commit_pending()
        event.remove(session, "after_commit", record_commit)
        self.assertEqual(len(commits), 1)

        self.assertIsNotNone(AbstractCustomerDAL.get_by_id(target.id))
        self.assertIsNone(AbstractCustomerDAL.get_by_id(source.id))
        self.assertEqual(AmoLeadDAL.get_by_id(301).abstract_customer_id, target.id)
        self.assertEqual(AmoLeadDAL.get_by_id(302).abstract_customer_id, target.id)
        self.assertEqual(
            db.session.scalar(select(db.func.count()).select_from(AbstractCustomerCompany)),
            1,
        )

    def test_cleanup_rolls_back_all_deletes_on_error(self):
        aggregate = self._aggregate()
        db.session.commit()
        state = SyncState()

        with patch.object(AmoCustomerDAL, "delete_not_in_ids", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                cleanup_stale_records(state)

        self.assertIsNotNone(AbstractCustomerDAL.get_by_id(aggregate.id))

    def test_successful_cleanup_deletes_stale_records_and_keeps_seen_ids(self):
        kept = self._aggregate()
        stale = self._aggregate()
        kept_id, stale_id = kept.id, stale.id
        db.session.add_all(
            [
                AmoCustomer(id=401, abstract_customer_id=kept.id, login="keep", name="Keep"),
                AmoCustomer(id=402, abstract_customer_id=stale.id, login="stale", name="Stale"),
            ]
        )
        db.session.commit()

        state = SyncState(
            abstract_customer_ids={kept_id},
            customer_ids={401},
        )
        cleanup_stale_records(state)

        self.assertIsNotNone(AbstractCustomerDAL.get_by_id(kept_id))
        self.assertIsNone(AbstractCustomerDAL.get_by_id(stale_id))
        self.assertIsNotNone(AmoCustomerDAL.get_by_id(401))
        self.assertIsNone(AmoCustomerDAL.get_by_id(402))

    def test_large_keep_id_set_uses_single_array_bind(self):
        company = AmoCompany(id=501, name="Company")
        db.session.add(company)
        db.session.commit()

        deleted = AmoCompanyDAL.delete_not_in_ids(range(65536))
        db.session.commit()

        self.assertEqual(deleted, 0)
        self.assertIsNotNone(AmoCompanyDAL.get_by_id(501))

    def test_writer_commits_after_500_rows_and_upserts_jsonb(self):
        session = db.session()
        commits = []
        inserts = []

        def record_commit(current):
            commits.append(1)

        def record_statement(connection, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("INSERT INTO AMO_COMPANY"):
                inserts.append(statement)

        event.listen(session, "after_commit", record_commit)
        event.listen(db.engine, "before_cursor_execute", record_statement)
        try:
            writer = SyncBatchWriter(batch_size=500)
            for company_id in range(1, 502):
                writer.upsert(
                    AmoCompany,
                    company_id,
                    {"name": "Company", "inn": None, "api_value": {"revision": 1}},
                )
                if company_id == 500:
                    self.assertEqual(len(commits), 1)
                    self.assertEqual(len(inserts), 1)
            writer.commit_pending()

            writer.upsert(
                AmoCompany,
                1,
                {"name": "Updated", "inn": "123", "api_value": {"revision": 2}},
            )
            writer.commit_pending()
        finally:
            event.remove(session, "after_commit", record_commit)
            event.remove(db.engine, "before_cursor_execute", record_statement)

        self.assertEqual(len(commits), 3)
        self.assertEqual(len(inserts), 3)
        saved = db.session.get(AmoCompany, 1)
        self.assertEqual(saved.name, "Updated")
        self.assertEqual(saved.api_value, {"revision": 2})
        self.assertEqual(db.session.scalar(select(db.func.count()).select_from(AmoCompany)), 501)

    def test_writer_failure_rolls_back_only_current_batch(self):
        writer = SyncBatchWriter(batch_size=500)
        for company_id in range(1, 501):
            writer.upsert(
                AmoCompany,
                company_id,
                {"name": "Company", "inn": None, "api_value": {"ok": True}},
            )
        self.assertIsNotNone(AmoCompanyDAL.get_by_id(1))

        writer.upsert(AmoCompany, 1000, {"api_value": {"invalid": True}})
        with self.assertRaises(Exception):
            writer.commit_pending()

        self.assertIsNotNone(AmoCompanyDAL.get_by_id(1))
        self.assertIsNone(AmoCompanyDAL.get_by_id(1000))

    def test_writer_inserts_relationship_pairs_without_duplicates(self):
        aggregate = self._aggregate()
        writer = SyncBatchWriter(batch_size=10)
        writer.upsert(
            AmoCompany,
            501,
            {"name": "Company", "inn": None, "api_value": {"active": True}},
        )
        pair = (aggregate.id, 501)
        writer.attach(AbstractCustomerCompany, pair)
        writer.attach(AbstractCustomerCompany, pair)
        writer.commit_pending()

        link_count = db.session.scalar(
            select(db.func.count()).select_from(AbstractCustomerCompany)
        )
        self.assertEqual(link_count, 1)

    def test_new_aggregates_reserve_sequence_ids_in_blocks(self):
        writer = SyncBatchWriter(batch_size=500)
        aggregates = [writer.new_aggregate() for _ in range(500)]
        aggregate_ids = {aggregate.id for aggregate in aggregates}

        writer.commit_pending()

        saved_count = db.session.scalar(
            select(db.func.count()).select_from(AbstractCustomer)
        )
        self.assertEqual(len(aggregate_ids), 500)
        self.assertEqual(saved_count, 500)


if __name__ == "__main__":
    import unittest

    unittest.main()
