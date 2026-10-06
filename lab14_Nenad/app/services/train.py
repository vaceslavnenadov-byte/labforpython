"""Бизнес-логика поездов."""

from sqlalchemy.exc import IntegrityError

from app.cache import Cache
from app.exceptions import AppError, ConflictError, NotFoundError
from app.models.train import Train
from app.repositories.train import SORT_FIELDS, TrainRepository
from app.schemas.train import TrainCreate, TrainResponse, TrainUpdate


class TrainService:
    def __init__(self, repository: TrainRepository, cache: Cache) -> None:
        self.repository = repository
        self.cache = cache

    @staticmethod
    def _key(train_id: int) -> str:
        return f"train:{train_id}"

    def _get_or_404(self, train_id: int) -> Train:
        train = self.repository.get(train_id)
        if train is None:
            raise NotFoundError(f"Train {train_id} not found")
        return train

    def list_trains(self, **params) -> tuple[list[Train], int]:
        if params["sort"] not in SORT_FIELDS:
            raise AppError(f"sort must be one of {sorted(SORT_FIELDS)}")
        return self.repository.list_trains(**params)

    def get_train(self, train_id: int) -> tuple[dict, bool]:
        """Возвращает (данные, получено_из_кэша)."""
        cached = self.cache.get(self._key(train_id))
        if cached is not None:
            return cached, True
        data = TrainResponse.model_validate(self._get_or_404(train_id)).model_dump(mode="json")
        self.cache.set(self._key(train_id), data)
        return data, False

    def create_train(self, data: TrainCreate) -> Train:
        if self.repository.get_by_number(data.number):
            raise ConflictError(f"Train {data.number} already exists")
        try:
            return self.repository.add(Train(**data.model_dump()))
        except IntegrityError:
            self.repository.db.rollback()
            raise ConflictError("Constraint violation") from None

    def replace_train(self, train_id: int, data: TrainCreate) -> Train:
        return self._apply(train_id, data.model_dump())

    def patch_train(self, train_id: int, data: TrainUpdate) -> Train:
        return self._apply(train_id, data.model_dump(exclude_unset=True))

    def _apply(self, train_id: int, fields: dict) -> Train:
        train = self._get_or_404(train_id)
        if "number" in fields and fields["number"] != train.number and self.repository.get_by_number(fields["number"]):
            raise ConflictError(f"Train {fields['number']} already exists")
        for key, value in fields.items():
            setattr(train, key, value)
        if train.arrival_time <= train.departure_time:
            self.repository.db.rollback()
            raise AppError("arrival_time must be later than departure_time")
        try:
            saved = self.repository.save(train)
        except IntegrityError:
            self.repository.db.rollback()
            raise ConflictError("Constraint violation") from None
        self.cache.delete(self._key(train_id))       # инвалидация
        return saved

    def delete_train(self, train_id: int) -> None:
        self.repository.delete(self._get_or_404(train_id))
        self.cache.delete(self._key(train_id))

    def search(self, query: str) -> list[Train]:
        return self.repository.search(query)

    def statistics(self) -> dict:
        return self.repository.statistics()
