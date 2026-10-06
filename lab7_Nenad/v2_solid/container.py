"""Простой контейнер зависимостей (доп. задание высокого уровня)."""

from typing import Any, Callable


class Container:
    def __init__(self) -> None:
        self._providers: dict[Any, tuple[Callable[[], Any], bool]] = {}
        self._instances: dict[Any, Any] = {}

    def register(self, interface: Any, provider: Callable[[], Any], singleton: bool = True) -> None:
        self._providers[interface] = (provider, singleton)
        self._instances.pop(interface, None)

    def resolve(self, interface: Any) -> Any:
        if interface in self._instances:
            return self._instances[interface]
        if interface not in self._providers:
            raise KeyError(f"Зависимость {getattr(interface, '__name__', interface)} не зарегистрирована")
        provider, singleton = self._providers[interface]
        instance = provider()
        if singleton:
            self._instances[interface] = instance
        return instance
