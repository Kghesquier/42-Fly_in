"""Tests of the Parser: valid files, defaults and every error case."""

from pathlib import Path

import pytest

from models.zone import ZoneType
from parsing.parser import ParseError, Parser

MAPS = Path(__file__).resolve().parent.parent / "maps"


def write_map(tmp_path: Path, content: str) -> str:
    """Write a map in a temporary file and return its path."""
    path = tmp_path / "map.txt"
    path.write_text(content)
    return str(path)


def test_subject_example(tmp_path: Path) -> None:
    content = (
        "nb_drones: 5\n\n"
        "start_hub: hub 0 0 [color=green]\n"
        "end_hub: goal 10 10 [color=yellow]\n"
        "# a comment\n"
        "hub: roof1 3 4 [zone=restricted color=red]\n"
        "hub: corridorA 4 3 [max_drones=2 zone=priority color=green]\n"
        "hub: obstacleX 5 5 [zone=blocked color=gray]\n"
        "connection: hub-roof1\n"
        "connection: roof1-goal\n"
        "connection: hub-corridorA [max_link_capacity=2]\n"
    )
    network, drones = Parser().parse(write_map(tmp_path, content))
    assert [d.drone_id for d in drones] == ["D1", "D2", "D3", "D4", "D5"]
    assert all(d.current_zone == "hub" for d in drones)
    assert network.start_zone.name == "hub"
    assert network.end_zone.name == "goal"
    corridor = network.get_zone("corridorA")
    assert corridor.zone_type == ZoneType.PRIORITY
    assert corridor.max_drones == 2
    assert network.get_zone("roof1").max_drones == 1
    assert network.get_zone("obstacleX").zone_type == ZoneType.BLOCKED
    assert network.get_connection("roof1", "hub").max_link_capacity == 1
    assert network.get_connection("corridorA", "hub").max_link_capacity == 2
    assert network.get_zone("hub").max_drones == float("inf")


def test_defaults(tmp_path: Path) -> None:
    content = (
        "nb_drones: 1\nstart_hub: s 0 0 [max_drones=1]\n"
        "hub: a -1 2\nend_hub: e 1 0\nconnection: s-a\n"
    )
    network, _ = Parser().parse(write_map(tmp_path, content))
    zone = network.get_zone("a")
    assert (zone.x, zone.y) == (-1, 2)
    assert zone.zone_type == ZoneType.NORMAL
    assert zone.color is None
    assert zone.max_drones == 1
    assert network.get_zone("s").max_drones == float("inf")


@pytest.mark.parametrize(
    "name",
    sorted(p.name for p in (MAPS / "invalid").glob("*.txt")),
)
def test_invalid_maps_raise_parse_error(name: str) -> None:
    with pytest.raises(ParseError) as info:
        Parser().parse(str(MAPS / "invalid" / name))
    assert str(info.value).startswith("Line ")


def test_error_message_points_to_line(tmp_path: Path) -> None:
    content = "nb_drones: 1\nstart_hub: s 0 0\nhub: a 1 0 [zone=lava]\n"
    with pytest.raises(ParseError) as info:
        Parser().parse(write_map(tmp_path, content))
    assert info.value.line_number == 3
    assert "lava" in info.value.message


@pytest.mark.parametrize(
    "path",
    sorted(str(p) for p in MAPS.glob("*/*.txt") if p.parent.name in (
        "easy", "medium", "hard", "challenger", "edge_cases"
    )),
)
def test_all_provided_maps_parse(path: str) -> None:
    network, drones = Parser().parse(path)
    assert drones
    assert network.zones
