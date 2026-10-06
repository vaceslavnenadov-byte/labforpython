"""Способы оплаты. Добавление нового — новый класс (OCP)."""

import uuid

from interfaces.services import PaymentMethod


class CardPayment(PaymentMethod):
    name = "банковская карта"
    COMMISSION = 0.015

    def total(self, amount: float) -> float:
        return round(amount * (1 + self.COMMISSION), 2)

    def pay(self, amount: float) -> str:
        return f"CARD-{uuid.uuid4().hex[:8]}"


class CashPayment(PaymentMethod):
    name = "наличные в кассе"

    def total(self, amount: float) -> float:
        return round(amount, 2)

    def pay(self, amount: float) -> str:
        return "CASH-RECEIPT"


class SbpPayment(PaymentMethod):
    """Система быстрых платежей — фиксированная комиссия 10 руб."""
    name = "СБП"

    def total(self, amount: float) -> float:
        return round(amount + 10, 2)

    def pay(self, amount: float) -> str:
        return f"SBP-{uuid.uuid4().hex[:6]}"


class BonusPayment(PaymentMethod):
    """Добавлен ПОСЛЕ написания BookingService — сервис не изменялся."""
    name = "бонусные баллы РЖД"

    def __init__(self, balance: float) -> None:
        self.balance = balance

    def total(self, amount: float) -> float:
        return round(amount, 2)

    def pay(self, amount: float) -> str:
        if amount > self.balance:
            raise ValueError(f"Недостаточно баллов: {self.balance} < {amount}")
        self.balance -= amount
        return "BONUS"
