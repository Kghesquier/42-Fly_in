"""End-to-end tests: every map is solved, validly, within its target."""

import subprocess
import sys
from pathlib import Path

import pytest

from algorithms.scheduler import NoPathError, Scheduler
from parsing.parser import Parser
from simulation.simulator import Simulator
from tests.output_validator import OutputValidator

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps"

# Mandatory limits of the subject (easy < 10, medium <= 30, hard < 60).
# The challenger map is optional: we only check that it is valid.
TARGETS = {
    "easy/01_linear_path.txt": 9,
    "easy/02_simple_fork.txt": 9,
    "easy/03_basic_capacity.txt": 9,
    "medium/01_dead_end_trap.txt": 30,
    "medium/02_circular_loop.txt": 30,
    "medium/03_priority_puzzle.txt": 30,
    "hard/01_maze_nightmare.txt": 59,
    "hard/02_capacity_hell.txt": 59,
    "hard/03_ultimate_challenge.txt": 59,
    "challenger/01_the_impossible_dream.txt": 200,
    "edge_cases/single_drone.txt": 4,
    "edge_cases/direct_link.txt": 2,
    "edge_cases/restricted_goal.txt": 6,
    "edge_cases/blocked_detour.txt": 5,
    "edge_cases/huge_capacity.txt": 2,
    "edge_cases/many_drones.txt": 100,
}


def simulate(map_path: Path) -> tuple[list[str], int]:
    """Run the full pipeline on a map.

    Returns:
        The output lines and the number of drones.
    """
    network, drones = Parser().parse(str(map_path))
    Scheduler(network).assign_paths(drones)
    simulator = Simulator(network, drones)
    lines: list[str] = []
    while not simulator.is_finished():
        lines.append(" ".join(simulator.step().moves))
    OutputValidator(network, len(drones)).validate(lines)
    return lines, len(drones)


@pytest.mark.parametrize("name,target", sorted(TARGETS.items()))
def test_map_is_valid_and_fast(name: str, target: int) -> None:
    lines, _ = simulate(MAPS / name)
    assert len(lines) <= target


@pytest.mark.parametrize(
    "name", ["disconnected_graph.txt", "blocked_only_path.txt"]
)
def test_unreachable_goal(name: str) -> None:
    network, _ = Parser().parse(str(MAPS / "edge_cases" / name))
    with pytest.raises(NoPathError):
        Scheduler(network)


def test_restricted_takes_two_turns() -> None:
    lines, _ = simulate(MAPS / "edge_cases" / "single_drone.txt")
    assert lines == ["D1-a", "D1-a-b", "D1-b", "D1-goal"]


def test_linear_path_output() -> None:
    lines, _ = simulate(MAPS / "easy" / "01_linear_path.txt")
    assert lines == [
        "D1-waypoint1",
        "D1-waypoint2 D2-waypoint1",
        "D1-goal D2-waypoint2",
        "D2-goal",
    ]


def test_priority_zone_is_preferred() -> None:
    lines, _ = simulate(MAPS / "medium" / "03_priority_puzzle.txt")
    assert lines[0].split()[0] == "D1-fast_junction"


def test_main_cli_output_and_errors() -> None:
    ok = subprocess.run(
        [sys.executable, "main.py", "maps/easy/01_linear_path.txt"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert ok.returncode == 0
    assert ok.stdout.splitlines()[0] == "D1-waypoint1"
    assert "\033" not in ok.stdout
    bad = subprocess.run(
        [sys.executable, "main.py", "maps/invalid/zero_capacity.txt"],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert bad.returncode == 1
    assert "Line 3" in bad.stderr
    assert "Traceback" not in bad.stderr
