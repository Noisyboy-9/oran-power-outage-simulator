import random

import networkx as nx

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
        self._connectivity_graph = self._create_connectivity_graph()

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

    def _create_connectivity_graph(self) -> nx.Graph:
        graph = nx.Graph()
        graph.add_nodes_from(self._rus, bipartite=0)
        graph.add_nodes_from(self._users, bipartite=1)

        coverage_radius = self._config.ru.coverage_radius
        for ru in self._rus:
            for user in self._users:
                distance = self._ru_locations[ru].distance_to(
                    self._user_locations[user]
                )
                if distance >= coverage_radius:
                    continue

                closeness = 1 - distance / coverage_radius
                random_factor = 1 - self._random.random()
                graph.add_edge(ru, user, weight=random_factor * closeness)

        return graph

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

    def get_connectivity_graph(self) -> nx.Graph:
        return self._connectivity_graph.copy()

    def get_connection_weight(self, user: User, ru: RU) -> float:
        owns_user = any(candidate is user for candidate in self._users)
        owns_ru = any(candidate is ru for candidate in self._rus)
        if not owns_user or not owns_ru:
            return 0.0

        edge = self._connectivity_graph.get_edge_data(user, ru)
        if edge is None:
            return 0.0
        return float(edge["weight"])
