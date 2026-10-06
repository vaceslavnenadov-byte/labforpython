"""Протоколы (структурные интерфейсы)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Reportable(Protocol):
    def get_report_data(self) -> str:
        ...


def print_report(item: Reportable) -> None:
    """Функция работает с любым объектом, имеющим get_report_data()."""
    print("[REPORT]", item.get_report_data())
