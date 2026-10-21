"""Scheduler: gives a path to every drone, spreading them over paths."""

from algorithms.path_finder import PathFinder
from models.drone import Drone
from models.network import Network


class NoPathError(Exception):
    """Raised when the end zone cannot be reached from the start zone."""


class Scheduler:
    """Chooses which path each drone will follow.

    Idea (like choosing the shortest queue at the supermarket): for
    each path we estimate when a new drone would arrive if it took it:

        estimate = path_cost + number_of_drones_already_on_this_path

    because, roughly, every drone in front of you delays you by one
    turn. Each drone takes the path with the smallest estimate, so the
    first drones take the shortest path and the next ones spread over
    the other paths when the shortest one gets too crowded.

    Attributes:
        network: the map.
        path_finder: the PathFinder used to compute the paths.
        paths: the candidate paths, the shortest one first.
    """

    def __init__(self, network: Network) -> None:
        self.network = network
        self.path_finder = PathFinder(network)
        start = network.start_zone.name
        end = network.end_zone.name
        self.paths = self.path_finder.find_paths(start, end)
        if not self.paths:
            raise NoPathError(
                f"no path from {start!r} to {end!r} "
                "(disconnected graph or blocked zones)"
            )

    def assign_paths(self, drones: list[Drone]) -> None:
        """Give a path to every drone (stored in drone.path).

        Args:
            drones: the drones to route, in order.
        """
        costs: list[int] = []
        for path in self.paths:
            costs.append(self.path_finder.path_cost(path))
        drones_on_path = [0] * len(self.paths)

        for drone in drones:
            best = 0
            for i in range(len(self.paths)):
                if (costs[i] + drones_on_path[i]
                        < costs[best] + drones_on_path[best]):
                    best = i
            drone.path = list(self.paths[best])
            drone.path_index = 0
            drones_on_path[best] += 1
