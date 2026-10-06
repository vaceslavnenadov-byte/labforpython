class TaxiError(Exception):
    """Базовая ошибка приложения."""


class NotFoundError(TaxiError):
    pass


class DuplicateError(TaxiError):
    pass


class ValidationError(TaxiError):
    pass


class BusinessRuleError(TaxiError):
    """Нарушение бизнес-правила (нет свободных водителей, неверный статус и т. п.)."""
