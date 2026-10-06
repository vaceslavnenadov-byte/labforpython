from interfaces.repository import TripReader
from models.entities import Trip


class SearchService:
    """Поиск рейсов. Зависит только от интерфейса чтения (ISP)."""

    def __init__(self, trips: TripReader) -> None:
        self.trips = trips

    def search(self, city: str = "", date: str | None = None, max_price: float | None = None) -> list[Trip]:
        result = []
        for trip in self.trips.get_all():
            if city and city.lower() not in trip.route.lower():
                continue
            if date and trip.date != date:
                continue
            if max_price is not None and trip.base_price > max_price:
                continue
            result.append(trip)
        return sorted(result, key=lambda t: (t.date, t.base_price))
