"""Абстракции внешних механизмов: оплата и уведомления."""

from abc import ABC, abstractmethod
from typing import Protocol


class PaymentMethod(ABC):
    """OCP: новый способ оплаты = новый подкласс, сервис не меняется."""

    name: str = "абстрактный"

    @abstractmethod
    def total(self, amount: float) -> float:
        """Сумма к оплате с учётом комиссии."""

    @abstractmethod
    def pay(self, amount: float) -> str:
        """Проводит платёж и возвращает идентификатор транзакции."""


class Notifier(Protocol):
    def send(self, recipient: str, message: str) -> None: ...
