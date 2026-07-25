from abc import ABC, abstractmethod

from simulator.domain.ru import RU


class RUController(ABC):
    @abstractmethod
    def update(self, rus: list[RU], timestamp: int) -> list[RU]:
        """Update statuses and return the trusted environment RU list.

        Controllers return the supplied RU instances after policy application;
        the environment trusts this handoff and adopts the returned list.
        """
