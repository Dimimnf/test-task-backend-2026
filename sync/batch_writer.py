from collections import defaultdict
from typing import Any, Dict, List, Tuple, Type

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from models.abstract_customer import AbstractCustomer
from models.base import db


class SyncBatchWriter:
    """Пакетирует upsert CRM-сущностей и вставку связей."""

    def __init__(self, batch_size: int = 500) -> None:
        if batch_size < 2:
            raise ValueError("batch_size должен быть не меньше двух")
        self.batch_size = batch_size
        self._rows: Dict[Type[Any], Dict[Any, Dict[str, Any]]] = defaultdict(dict)
        self._links: Dict[Type[Any], set] = defaultdict(set)
        self._aggregate_ids: List[int] = []
        self._pending_aggregate_count = 0
        self.generation = 0

    @property
    def _size(self) -> int:
        """Общее число незакоммиченных строк, связей и новых агрегатов."""
        return (
            sum(len(rows) for rows in self._rows.values())
            + sum(len(links) for links in self._links.values())
            + self._pending_aggregate_count
        )

    @_size.setter
    def _size(self, value: int) -> None:
        """Выравнивает счётчик агрегатов под желаемое общее значение.

        Используется тестовыми заглушками для сброса размера батча;
        внутренний код изменяет `_pending_aggregate_count` напрямую.
        """
        base = sum(len(rows) for rows in self._rows.values()) + sum(
            len(links) for links in self._links.values()
        )
        self._pending_aggregate_count = max(0, value - base)

    def new_aggregate(self) -> AbstractCustomer:
        """Создаёт агрегат с ID из заранее полученного диапазона sequence."""
        if self._size and self._size + 2 > self.batch_size:
            self.commit_pending()
        if not self._aggregate_ids:
            self._reserve_aggregate_ids(self.batch_size)
        aggregate = AbstractCustomer(id=self._aggregate_ids.pop(0))
        db.session.add(aggregate)
        self._pending_aggregate_count += 1
        return aggregate

    def upsert(self, model: Type[Any], entity_id: Any, values: Dict[str, Any]) -> None:
        """Добавляет строку на вставку или обновление по первичному ключу."""
        rows = self._rows[model]
        rows[entity_id] = {"id": entity_id, **values}
        self._flush_if_full()

    def attach(self, model: Type[Any], values: Tuple[int, int]) -> None:
        """Добавляет уникальную пару ключей связующей таблицы."""
        links = self._links[model]
        if values not in links:
            links.add(values)
        self._flush_if_full()

    def redirect_aggregate(self, source_id: int, target_id: int) -> None:
        """Перенаправляет ещё не записанные сущности и связи при merge."""
        self._redirect_rows(source_id, target_id)
        self._redirect_links(source_id, target_id)

    def commit_pending(self) -> None:
        """Записывает накопленные строки одним ограниченным набором запросов."""
        if not self._size:
            return
        try:
            self._commit_rows()
            self._commit_links()
            db.session.commit()
            db.session.expire_all()
            self.generation += 1
        except Exception:
            db.session.rollback()
            raise
        finally:
            self._rows.clear()
            self._links.clear()
            self._aggregate_ids.clear()
            self._pending_aggregate_count = 0

    def rollback(self) -> None:
        """Откатывает незавершённый батч и очищает его буферы."""
        db.session.rollback()
        self._rows.clear()
        self._links.clear()
        self._aggregate_ids.clear()
        self._pending_aggregate_count = 0

    def _reserve_aggregate_ids(self, count: int) -> None:
        """Резервирует блок ID из sequence таблицы abstract_customer."""
        seq_name = func.pg_get_serial_sequence("abstract_customer", "id")
        ids = db.session.execute(
            db.select(func.nextval(seq_name)).select_from(func.generate_series(1, count))
        ).scalars()
        self._aggregate_ids.extend(ids.all())

    def _redirect_rows(self, source_id: int, target_id: int) -> None:
        """Перенаправляет незаписанные строки к целевому агрегату."""
        for rows in self._rows.values():
            for row in rows.values():
                if row.get("abstract_customer_id") == source_id:
                    row["abstract_customer_id"] = target_id

    def _redirect_links(self, source_id: int, target_id: int) -> None:
        """Перенаправляет незаписанные связи к целевому агрегату."""
        for links in self._links.values():
            redirected = {
                (target_id if aggregate_id == source_id else aggregate_id, entity_id)
                for aggregate_id, entity_id in links
            }
            links.clear()
            links.update(redirected)

    def _commit_rows(self) -> None:
        """Выполняет INSERT .. ON CONFLICT DO UPDATE для накопленных строк."""
        for model, rows in self._rows.items():
            if not rows:
                continue
            table = model.__table__
            values = list(rows.values())
            statement = insert(table).values(values)
            update_values = {
                column.name: getattr(statement.excluded, column.name)
                for column in table.columns
                if column.primary_key is False and column.name in values[0]
            }
            if update_values:
                primary_key = list(table.primary_key.columns)[0]
                statement = statement.on_conflict_do_update(
                    index_elements=[primary_key],
                    set_=update_values,
                )
                db.session.execute(statement)

    def _commit_links(self) -> None:
        """Выполняет INSERT .. ON CONFLICT DO NOTHING для связей."""
        for model, links in self._links.items():
            if not links:
                continue
            table = model.__table__
            columns = list(table.primary_key.columns)
            values = [dict(zip((column.name for column in columns), pair)) for pair in links]
            statement = insert(table).values(values).on_conflict_do_nothing()
            db.session.execute(statement)

    def _flush_if_full(self) -> None:
        """Фиксирует пакет при достижении настроенного лимита строк."""
        if self._size >= self.batch_size:
            self.commit_pending()
