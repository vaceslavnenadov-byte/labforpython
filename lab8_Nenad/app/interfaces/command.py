from typing import Protocol


class Command(Protocol):
    name: str

    def execute(self) -> object: ...
    def undo(self) -> None: ...
