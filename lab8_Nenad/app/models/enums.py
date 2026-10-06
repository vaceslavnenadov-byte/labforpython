from enum import Enum


class TicketStatus(Enum):
    SOLD = "продан"
    REFUNDED = "возвращён"


class WagonCategory(Enum):
    SEATED = "seated"
    COUPE = "coupe"
    SV = "sv"
