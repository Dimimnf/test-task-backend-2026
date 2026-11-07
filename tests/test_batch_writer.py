import unittest

from models import AmoCustomer, AbstractCustomerContact
from sync.batch_writer import SyncBatchWriter


class RecordingBatchWriter(SyncBatchWriter):
    """Собирает границы батчей без подключения к PostgreSQL."""

    def __init__(self, batch_size=500):
        super().__init__(batch_size)
        self.committed = []

    def commit_pending(self):
        if not self._size:
            return
        self.committed.append((dict(self._rows), dict(self._links), self._size))
        self._rows.clear()
        self._links.clear()
        self._size = 0


class SyncBatchWriterTests(unittest.TestCase):
    """Проверяет накопление строк и ограничение размера батча."""

    def test_flushes_at_configured_size(self):
        writer = RecordingBatchWriter(batch_size=2)

        writer.upsert(AmoCustomer, 1, {"name": "first"})
        writer.upsert(AmoCustomer, 2, {"name": "second"})

        self.assertEqual(len(writer.committed), 1)
        self.assertEqual(writer.committed[0][2], 2)

    def test_deduplicates_pending_ids_and_link_pairs(self):
        writer = RecordingBatchWriter(batch_size=10)
        writer.upsert(AmoCustomer, 1, {"name": "old"})
        writer.upsert(AmoCustomer, 1, {"name": "new"})
        writer.attach(AbstractCustomerContact, (10, 20))
        writer.attach(AbstractCustomerContact, (10, 20))

        self.assertEqual(writer._size, 2)
        self.assertEqual(writer._rows[AmoCustomer][1]["name"], "new")
        self.assertEqual(writer._links[AbstractCustomerContact], {(10, 20)})

    def test_rejects_non_positive_batch_size(self):
        with self.assertRaises(ValueError):
            SyncBatchWriter(batch_size=0)


if __name__ == "__main__":
    unittest.main()
