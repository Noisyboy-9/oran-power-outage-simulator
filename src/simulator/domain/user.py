from dataclasses import dataclass

from simulator.domain.errors import DomainValidationError


@dataclass(frozen=True)
class User:
    id: int

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise DomainValidationError("id must be positive")
