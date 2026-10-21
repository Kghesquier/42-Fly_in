"""Drone: represents a single drone moving through the network."""


class Drone:
    """A single drone navigating from start to end.

    Unlike Zone and Connection, a Drone DOES carry its own dynamic
    state (it's the entity that moves), rather than delegating it to
    the Simulator.

    Attributes:
        drone_id: unique identifier, e.g. "D1".
        current_zone: name of the zone the drone currently occupies.
            None while the drone is mid-transit on a restricted
            connection (it hasn't "arrived" anywhere yet).
        destination: name of the zone the drone is currently moving
            toward. None if the drone isn't moving right now.
        turns_remaining: turns left before reaching destination.
            0 means "not currently mid-transit".
        delivered: True once the drone has reached the end zone.
        path: the zones the drone must follow, from start to end
            (given by the Scheduler).
        path_index: position of the drone in path (0 = start zone).
    """

    def __init__(self, drone_id: str, start_zone: str) -> None:
        self.drone_id = drone_id
        self.current_zone: str | None = start_zone
        self.destination: str | None = None
        self.turns_remaining = 0
        self.delivered = False
        self.path: list[str] = [start_zone]
        self.path_index = 0

    def next_zone(self) -> str | None:
        """Return the next zone on the drone's path.

        Returns:
            The name of the next zone, or None if the drone is already
            at the end of its path.
        """
        if self.path_index + 1 < len(self.path):
            return self.path[self.path_index + 1]
        return None

    def is_moving(self) -> bool:
        """Return whether the drone is currently mid-transit.

        Returns:
            True if turns_remaining > 0.
        """
        return self.turns_remaining > 0

    def start_move(self, destination: str, cost: int) -> None:
        """Begin moving toward a destination zone.

        Args:
            destination: name of the zone being moved toward.
            cost: number of turns required (1 for normal/priority,
                2 for restricted — see Zone.movement_cost).
        """
        self.destination = destination
        self.turns_remaining = cost
        self.current_zone = None

    def advance_turn(self) -> None:
        """Progress the drone by one turn toward its destination.

        If this was the last turn needed, the drone arrives: its
        current_zone becomes the destination, and destination/
        turns_remaining reset.
        """
        if self.turns_remaining > 0:
            self.turns_remaining -= 1
            if self.turns_remaining == 0:
                self.current_zone = self.destination
                self.destination = None

    def mark_delivered(self) -> None:
        """Mark this drone as having reached the end zone."""
        self.delivered = True

    def __repr__(self) -> str:
        return (
            f"Drone({self.drone_id!r}, "
            f"zone={self.current_zone!r}, "
            f"delivered={self.delivered})"
        )
