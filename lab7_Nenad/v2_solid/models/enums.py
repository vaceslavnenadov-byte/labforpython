from enum import Enum


class TicketStatus(Enum):
    BOOKED = "забронирован"
    PAID = "оплачен"
    REFUNDED = "возвращён"
