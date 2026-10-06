from interfaces.repository import TicketReader, TripReader
from models.enums import TicketStatus


class ReportService:
    """Формирует данные отчёта, но не печатает их (печать — задача UI)."""

    def __init__(self, trips: TripReader, tickets: TicketReader) -> None:
        self.trips = trips
        self.tickets = tickets

    def sales_report(self) -> list[dict]:
        rows = []
        for trip in self.trips.get_all():
            sold = [t for t in self.tickets.find_by_trip(trip.id) if t.status == TicketStatus.PAID]
            rows.append({
                "train": trip.train_number,
                "route": trip.route,
                "sold": len(sold),
                "load_percent": round(len(sold) / trip.seats * 100, 1),
                "revenue": round(sum(t.price for t in sold), 2),
            })
        return rows
