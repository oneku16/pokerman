import re
import secrets
from dataclasses import dataclass

_CODE_PATTERN = re.compile(r"^\d{4}$")


@dataclass(frozen=True, slots=True)
class RoomCode:
    value: str

    def __post_init__(self) -> None:
        if not _CODE_PATTERN.fullmatch(self.value):
            raise ValueError(f"room code must be exactly 4 digits, got {self.value!r}")

    @classmethod
    def generate(cls) -> "RoomCode":
        return cls(f"{secrets.randbelow(10_000):04d}")

    def __str__(self) -> str:
        return self.value
