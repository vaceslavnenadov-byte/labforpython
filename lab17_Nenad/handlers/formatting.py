from database.models import Ticket, TicketStatus, Train


def train_text(train: Train) -> str:
    return (f"🚆 <b>{train.title}</b>\n"
            f"{train.from_station.name} → {train.to_station.name}\n"
            f"Отправление: {train.departure:%d.%m.%Y %H:%M}, прибытие: {train.arrival:%d.%m.%Y %H:%M}\n"
            f"Цена: от {train.base_price:.0f} ₽")


def ticket_text(ticket: Ticket) -> str:
    status = "действует" if ticket.status == TicketStatus.ACTIVE else "возвращён"
    return (f"🎫 <b>Билет №{ticket.id}</b> ({status})\n"
            f"Поезд {ticket.train.title}: {ticket.train.from_station.city} → {ticket.train.to_station.city}\n"
            f"Отправление: {ticket.train.departure:%d.%m.%Y %H:%M}\n"
            f"Вагон: {ticket.wagon_type.title}, место {ticket.seat}\n"
            f"Пассажир: {ticket.passenger_name}\nЦена: {ticket.price:.2f} ₽")
