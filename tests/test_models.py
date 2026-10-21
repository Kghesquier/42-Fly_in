"""Unit tests of the models and the PathFinder."""

import pytest

from algorithms.path_finder import PathFinder
from models.connection import Connection
from models.drone import Drone
from models.network import Network
from models.zone import Zone, ZoneType


def build_network() -> Network:
    """start - a(restricted) - goal, and start - b - c - goal."""
    network = Network()
    network.add_zone(Zone("start", 0, 0, is_start=True))
    network.add_zone(Zone("a", 1, 0, zone_type=ZoneType.RESTRICTED))
    network.add_zone(Zone("b", 1, 1))
    network.add_zone(Zone("c", 2, 1, zone_type=ZoneType.PRIORITY))
    network.add_zone(Zone("goal", 3, 0, is_end=True))
    for zone_a, zone_b in [
        ("start", "a"), ("a", "goal"), ("start", "b"),
        ("b", "c"), ("c", "goal"),
    ]:
        network.add_connection(Connection(zone_a, zone_b))
    return network


def test_zone_costs_and_capacity() -> None:
    assert Zone("n", 0, 0).movement_cost == 1
    assert Zone("p", 0, 0, ZoneType.PRIORITY).movement_cost == 1
    assert Zone("r", 0, 0, ZoneType.RESTRICTED).movement_cost == 2
    blocked = Zone("x", 0, 0, ZoneType.BLOCKED)
    assert not blocked.can_enter()
    with pytest.raises(ValueError):
        _ = blocked.movement_cost
    zone = Zone("z", 0, 0, max_drones=2)
    assert zone.can_accept(1)
    assert not zone.can_accept(2)
    assert Zone("s", 0, 0, max_drones=1, is_start=True).can_accept(10**6)


def test_connection() -> None:
    connection = Connection("a", "b", 2)
    assert connection.name == "a-b"
    assert connection.other_end("b") == "a"
    assert connection.can_traverse(1)
    assert not connection.can_traverse(2)
    with pytest.raises(ValueError):
        connection.other_end("z")


def test_network_lookup() -> None:
    network = build_network()
    assert sorted(network.neighbors("start")) == ["a", "b"]
    assert network.has_connection("goal", "a")
    assert network.get_connection("goal", "c").name == "c-goal"
    with pytest.raises(ValueError):
        network.get_connection("start", "goal")


def test_drone_restricted_move() -> None:
    drone = Drone("D1", "start")
    drone.start_move("a", 2)
    drone.advance_turn()
    assert drone.is_moving() and drone.current_zone is None
    drone.advance_turn()
    assert not drone.is_moving() and drone.current_zone == "a"


def test_path_finder() -> None:
    network = build_network()
    finder = PathFinder(network)
    path = finder.shortest_path("start", "goal")
    assert finder.path_cost(["start", "a", "goal"]) == 3
    assert finder.path_cost(["start", "b", "c", "goal"]) == 3
    # equal cost: the path through the priority zone c is preferred
    assert path == ["start", "b", "c", "goal"]
    paths = finder.find_paths("start", "goal")
    assert paths == [["start", "b", "c", "goal"], ["start", "a", "goal"]]


def test_path_finder_no_path() -> None:
    network = Network()
    network.add_zone(Zone("s", 0, 0, is_start=True))
    network.add_zone(Zone("e", 1, 0, is_end=True))
    with pytest.raises(ValueError):
        PathFinder(network).shortest_path("s", "e")
