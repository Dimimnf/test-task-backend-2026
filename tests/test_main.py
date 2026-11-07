import unittest
from inspect import isgeneratorfunction
from unittest.mock import patch

from amocrm import amocrm_get
from main import collect_leads_customers


class WriterStub:
    instances = []

    def __init__(self, batch_size):
        self.rolled_back = False
        self.instances.append(self)

    def commit_pending(self):
        pass

    def rollback(self):
        self.rolled_back = True


class MainFailureTests(unittest.TestCase):
    """Проверяет, что прерванный сбор не запускает cleanup."""

    def test_collection_error_skips_cleanup_and_rolls_back_current_batch(self):
        WriterStub.instances.clear()
        with patch("main.SyncBatchWriter", WriterStub):
            with patch("main.collect_customers"):
                with patch("main.collect_leads", side_effect=RuntimeError("CRM error")):
                    with patch("main.cleanup_stale_records") as cleanup:
                        with self.assertRaises(RuntimeError):
                            collect_leads_customers(is_full=True)

        cleanup.assert_not_called()
        self.assertTrue(WriterStub.instances[0].rolled_back)

    def test_crm_reader_is_a_lazy_generator(self):
        self.assertTrue(isgeneratorfunction(amocrm_get))


if __name__ == "__main__":
    unittest.main()
