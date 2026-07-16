import random

from simulator.domain.map_cell import MapCell
from simulator.domain.ru import RU
from simulator.domain.user import User
from simulator.environment.config import EnvironmentConfig


class Environment:
    def __init__(self, config: EnvironmentConfig) -> None:
        self._config = config
        self._random = random.Random(config.random_seed)
        self._map = self._create_map()
        self._rus = self._create_rus()
        self._users = self._create_users()
        self._ru_locations: dict[RU, MapCell] = {}
        self._user_locations: dict[User, MapCell] = {}
        self._place_entities()

    def _create_map(self) -> list[list[MapCell]]:
        return [
            [MapCell(x=x, y=y) for x in range(self._config.map.width)]
            for y in range(self._config.map.height)
        ]

    def _create_rus(self) -> list[RU]:
        config = self._config.ru
        return [
            RU(
                id=ru_id,
                battery=config.initial_battery,
                status=config.initial_status,
                active_consumption=config.active_consumption,
                sleep_consumption=config.sleep_consumption,
            )
            for ru_id in range(1, config.count + 1)
        ]

    def _create_users(self) -> list[User]:
        return [User(id=user_id) for user_id in range(1, self._config.user_count + 1)]

    def _place_entities(self) -> None:
        available_cells = [cell for row in self._map for cell in row]
        entities: list[RU | User] = [*self._rus, *self._users]
        selected_cells = self._random.sample(available_cells, len(entities))

        for entity, cell in zip(entities, selected_cells, strict=True):
            occupied_cell = MapCell(x=cell.x, y=cell.y, occupant=entity)
            self._map[cell.y][cell.x] = occupied_cell
            if isinstance(entity, RU):
                self._ru_locations[entity] = occupied_cell
            else:
                self._user_locations[entity] = occupied_cell

    def get_map(self) -> list[list[MapCell]]:
        return [row.copy() for row in self._map]

    def get_rus(self) -> list[RU]:
        return self._rus.copy()

    def get_users(self) -> list[User]:
        return self._users.copy()

    def get_ru_locations(self) -> dict[RU, MapCell]:
        return self._ru_locations.copy()

    def get_user_locations(self) -> dict[User, MapCell]:
        return self._user_locations.copy()
