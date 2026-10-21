"""Connection: represents a bidirectional link between two zones."""


class Connection:
    """A bidirectional connection (edge) between two zones.

    Like Zone, a Connection only holds STATIC configuration (which two
    zones it links, and its capacity). It does NOT track how many
    drones are currently traversing it — that dynamic state belongs to
    the Simulator.

    Attributes:
        zone_a: Name of one end of the connection.
        zone_b: Name of the other end of the connection.
        max_link_capacity: Maximum number of drones that can traverse
            this connection simultaneously.
    """

    def __init__(
        self,
        zone_a: str,
        zone_b: str,
        max_link_capacity: int = 1,
    ) -> None:
        self.zone_a = zone_a
        self.zone_b = zone_b
        self.max_link_capacity = max_link_capacity

    @property
    def name(self) -> str:
        """Return the connection's name as written in the map file.

        Used in the simulation output for drones in flight toward a
        restricted zone, e.g. "D1-hub-roof1".

        Returns:
            "<zone_a>-<zone_b>".
        """
        return f"{self.zone_a}-{self.zone_b}"

    def connects(self, zone_name: str) -> bool:
        """Return whether this connection touches the given zone.

        Args:
            zone_name: name of a zone to check.

        Returns:
            True if zone_name is one of the two ends of this connection.
        """
        return zone_name == self.zone_a or zone_name == self.zone_b

    def other_end(self, zone_name: str) -> str:
        """Given one end of the connection, return the other end.

        Args:
            zone_name: name of one of the two zones this connection links.

        Returns:
            The name of the opposite zone.

        Raises:
            ValueError: if zone_name is not one of the two ends.
        """
        if zone_name == self.zone_a:
            return self.zone_b
        elif zone_name == self.zone_b:
            return self.zone_a
        else:
            raise ValueError(
                "zone_name is incorrect"
                " or do not belong to zone_a or zone_b"
            )

    def can_traverse(self, current_traffic: int) -> bool:
        """Return whether one more drone can use this connection right now.

        Args:
            current_traffic: how many drones are currently traversing
                this connection (tracked and passed in by the Simulator).

        Returns:
            True if adding one more drone would not exceed
            max_link_capacity.
        """
        return current_traffic < self.max_link_capacity

    def __repr__(self) -> str:
        return f"Connection({self.zone_a!r}-{self.zone_b!r})"
