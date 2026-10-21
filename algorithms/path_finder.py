"""PathFinder: computes shortest (lowest-cost) paths through a Network."""

from models.network import Network
from models.zone import Zone, ZoneType


class PathFinder:
    """Computes shortest paths in a Network using Dijkstra's algorithm.

    Attributes:
        network: the Network to search paths in.
    """

    # Extra cost added to a zone already used by a previous path, so the
    # next search tries to go around it (see find_paths).
    USED_ZONE_PENALTY = 100

    # Priority zones cost 1 turn like normal zones, but we make them a
    # tiny bit cheaper so Dijkstra picks them when two paths are equal.
    # Must stay strictly below 1: Dijkstra needs every step cost > 0,
    # a negative cost breaks it (wrong paths, or even an infinite loop).
    PRIORITY_BONUS = 0.1

    def __init__(self, network: Network) -> None:
        self.network = network

    def _pick_next_zone(
        self,
        distances: dict[str, float],
        visited: set[str],
    ) -> str | None:
        """Pick the unvisited zone with the smallest known distance.

        Args:
            distances: maps each zone name to its currently known
                lowest cost from the start zone.
            visited: names of zones already fully processed.

        Returns:
            The name of the best unvisited zone to process next, or
            None if every remaining unvisited zone is unreachable
            (still at infinity).
        """
        best_zone: str | None = None
        best_distance = float("inf")

        for zone_name, distance in distances.items():
            if zone_name not in visited and distance < best_distance:
                best_distance = distance
                best_zone = zone_name

        return best_zone

    def _step_cost(self, zone: Zone, penalties: dict[str, int]) -> float:
        """Return the cost Dijkstra uses to enter a zone.

        Args:
            zone: the zone being entered.
            penalties: extra cost per zone name (may be empty).

        Returns:
            movement_cost, minus a small bonus for priority zones,
            plus the penalty of the zone if it has one.
        """
        cost: float = zone.movement_cost
        if zone.zone_type == ZoneType.PRIORITY:
            cost -= self.PRIORITY_BONUS
        return cost + penalties.get(zone.name, 0)

    def shortest_path(
        self,
        start: str,
        end: str,
        penalties: dict[str, int] | None = None,
    ) -> list[str]:
        """Compute the lowest-cost path from start to end.

        Uses Dijkstra's algorithm: repeatedly picks the cheapest
        unvisited zone, and tries to improve the cost of its
        neighbors through it.

        Args:
            start: name of the starting zone.
            end: name of the destination zone.
            penalties: optional extra cost per zone name.

        Returns:
            The list of zone names to visit, in order, INCLUDING both
            start and end. E.g. ["start", "waypoint1", "goal"].

        Raises:
            ValueError: if no path exists between start and end.
        """
        if penalties is None:
            penalties = {}

        distances: dict[str, float] = {}
        for zone_name in self.network.zones:
            distances[zone_name] = float("inf")
        distances[start] = 0.0

        previous: dict[str, str | None] = {}
        for zone_name in self.network.zones:
            previous[zone_name] = None

        visited: set[str] = set()

        while True:
            current = self._pick_next_zone(distances, visited)
            if current is None:
                raise ValueError(
                    f"No path exists between {start!r} and {end!r}"
                )
            elif current == end:
                break
            visited.add(current)

            for neighbor_name in self.network.neighbors(current):
                neighbor_zone = self.network.get_zone(neighbor_name)

                if not neighbor_zone.can_enter():
                    continue

                new_distance = distances[current] + self._step_cost(
                    neighbor_zone, penalties
                )

                if new_distance < distances[neighbor_name]:
                    distances[neighbor_name] = new_distance
                    previous[neighbor_name] = current

        path: list[str] = []
        current_position: str | None = end

        while current_position is not None:
            path.append(current_position)
            current_position = previous[current_position]

        path.reverse()
        return path

    def path_cost(self, path: list[str]) -> int:
        """Return the number of turns needed to follow a path alone.

        Args:
            path: zone names from start to end.

        Returns:
            The sum of the movement costs of every zone entered.
        """
        total = 0
        for zone_name in path[1:]:
            total += self.network.get_zone(zone_name).movement_cost
        return total

    def find_paths(
        self, start: str, end: str, max_paths: int = 5
    ) -> list[list[str]]:
        """Find several different paths from start to end.

        After each Dijkstra, every zone of the path found gets a big
        penalty, so the next Dijkstra prefers other zones. We stop when
        the same path comes back (no real alternative left).

        Args:
            start: name of the starting zone.
            end: name of the destination zone.
            max_paths: maximum number of paths to return.

        Returns:
            The paths found, the first one being the shortest. Empty
            if end cannot be reached.
        """
        paths: list[list[str]] = []
        penalties: dict[str, int] = {}

        for _ in range(max_paths):
            try:
                path = self.shortest_path(start, end, penalties)
            except ValueError:
                break
            if path in paths:
                break
            paths.append(path)
            for zone_name in path[1:-1]:
                penalties[zone_name] = (
                    penalties.get(zone_name, 0) + self.USED_ZONE_PENALTY
                )

        return paths
