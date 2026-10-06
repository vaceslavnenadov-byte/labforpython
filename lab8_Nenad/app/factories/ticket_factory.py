"""Factory: создание билета нужного типа по категории вагона."""

from models.entities import CoupeTicket, SeatedTicket, SvTicket, Ticket
from models.enums import WagonCategory


class TicketFactory:
    _registry: dict[WagonCategory, type[Ticket]] = {
        WagonCategory.SEATED: SeatedTicket,
        WagonCategory.COUPE: CoupeTicket,
        WagonCategory.SV: SvTicket,
    }

    @classmethod
    def register(cls, category: WagonCategory, ticket_class: type[Ticket]) -> None:
        """Позволяет добавить новый тип билета без изменения фабрики."""
        cls._registry[category] = ticket_class

    @classmethod
    def create(cls, category: WagonCategory | str, ticket_id: int, train_number: str,
               passenger: str, seat: int) -> Ticket:
        if isinstance(category, str):
            try:
                category = WagonCategory(category)
            except ValueError:
                raise ValueError(f"Неизвестный тип вагона: {category}") from None
        return cls._registry[category](ticket_id, train_number, passenger, seat)
