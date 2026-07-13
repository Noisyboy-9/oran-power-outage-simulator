from abc import ABC, abstractmethod

from simulator.domain.ru import RU


class RUController(ABC):
    @abstractmethod
    def update(self, rus: list[RU], timestamp: int) -> None:
        """Update RU statuses for the supplied timestamp."""
