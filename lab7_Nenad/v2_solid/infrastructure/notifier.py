"""Реализации уведомлений."""


class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"[УВЕДОМЛЕНИЕ → {recipient}] {message}")


class EmailNotifier:
    """Имитация email: письма накапливаются в «исходящих»."""

    def __init__(self) -> None:
        self.outbox: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.outbox.append((recipient, message))
        print(f"[EMAIL → {recipient}] {message}")


class SilentNotifier:
    def send(self, recipient: str, message: str) -> None:
        pass
