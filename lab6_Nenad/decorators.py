"""Собственные декораторы."""

import time
from functools import wraps
from typing import Any, Callable

from exceptions import InvalidStatusError


def log_call(func: Callable) -> Callable:
    """№1. Журналирование вызова: имя, аргументы, результат или исключение."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        shown_args = [repr(a) for a in args[1:]] + [f"{k}={v!r}" for k, v in kwargs.items()]
        print(f"[LOG] вызван {func.__name__}({', '.join(shown_args)})")
        try:
            result = func(*args, **kwargs)
        except Exception as error:
            print(f"[LOG] {func.__name__} -> исключение {type(error).__name__}: {error}")
            raise
        print(f"[LOG] {func.__name__} -> {result!r:.80}")
        return result
    return wrapper


def timing(func: Callable) -> Callable:
    """№2. Измерение времени выполнения."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"[PERFORMANCE] {func.__name__}: {time.perf_counter() - start:.6f} sec")
    return wrapper


def require_status(*allowed):
    """№3. Декоратор с параметрами: метод билета выполняется только в разрешённых статусах."""
    def decorator(method: Callable) -> Callable:
        @wraps(method)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            if self.status not in allowed:
                names = ", ".join(s.value for s in allowed)
                raise InvalidStatusError(
                    f"{method.__name__}: билет в статусе «{self.status.value}», допустимо: {names}"
                )
            return method(self, *args, **kwargs)
        return wrapper
    return decorator


def retry(times: int, exceptions: tuple = (Exception,), delay: float = 0.0):
    """№4. Повтор выполнения при ошибке (декоратор с параметрами)."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as error:
                    print(f"[RETRY] {func.__name__}: попытка {attempt}/{times} неудачна ({error})")
                    if attempt == times:
                        raise
                    time.sleep(delay)
        return wrapper
    return decorator


def command(title: str, order: int):
    """Регистрирует метод как пункт меню (доп. задание повышенной сложности).

    Пункты меню затем обнаруживаются через inspect.getmembers()."""
    def decorator(func: Callable) -> Callable:
        func.menu_title = title
        func.menu_order = order
        return func
    return decorator
