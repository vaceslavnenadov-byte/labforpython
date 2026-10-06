"""Контекстные менеджеры."""

import copy
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path


class Transaction:
    """Транзакционный режим для сервиса: при исключении состояние откатывается."""

    def __init__(self, service):
        self.service = service
        self._snapshot = None

    def __enter__(self):
        self._snapshot = copy.deepcopy((self.service.trains, self.service.tickets, self.service._next_id))
        print("[TRANSACTION] начало")
        return self.service

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type is not None:
            self.service.trains, self.service.tickets, self.service._next_id = self._snapshot
            print(f"[TRANSACTION] откат из-за {exc_type.__name__}: {exc_value}")
        else:
            print("[TRANSACTION] фиксация изменений")
        return False  # исключение пробрасывается дальше


class OperationLogger:
    """Записывает в файл дату, операцию, параметры, длительность, результат и исключение."""

    def __init__(self, operation: str, path: str | Path = "operations.log", **params):
        self.operation = operation
        self.path = Path(path)
        self.params = params

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        duration = time.perf_counter() - self.start
        lines = [
            f"[{datetime.now():%Y-%m-%d %H:%M:%S}]",
            f"Operation: {self.operation}",
            f"Params: {self.params}",
            f"Duration: {duration:.4f} sec",
            f"Result: {'ERROR' if exc_type else 'SUCCESS'}",
        ]
        if exc_type:
            lines.append(f"Exception: {exc_type.__name__}: {exc_value}")
        with open(self.path, "a", encoding="utf-8") as file:
            file.write("\n".join(lines) + "\n\n")
        return False


@contextmanager
def measure(block_name: str):
    """Контекстный менеджер на основе генератора: время выполнения блока."""
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"[BLOCK] {block_name}: {time.perf_counter() - start:.6f} sec")
