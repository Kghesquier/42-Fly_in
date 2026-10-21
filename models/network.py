"""Network: the graph of zones and connections."""

from models.connection import Connection
from models.zone import Zone


class Network:
    """The full graph of the drone map: zones + connections between them.

    The graph is stored as an adjacency list: for every zone name we
    keep the list of neighbor names. This makes neighbors() O(degree)
    instead of O(number of connections).

    Attributes:
        zones: Maps a zone name to its Zone instance, for O(1) lookup.
        connections: All connections in the network (unordered list).
    """

    def __init__(self) -> None:
        self.zones: dict[str, Zone] = {}
        self.connections: list[Connection] = []
        self._adjacency: dict[str, list[str]] = {}
        self._connection_index: dict[frozenset[str], Connection] = {}

    def add_zone(self, zone: Zone) -> None:
        """Register a new zone in the network.

        Args:
            zone: the Zone instance to add.
        """
        self.zones[zone.name] = zone
        self._adjacency.setdefault(zone.name, [])

    def add_connection(self, connection: Connection) -> None:
        """Register a new connection in the network.

        Args:
            connection: the Connection instance to add. Both of its
                zones must already have been added.
        """
        self.connections.append(connection)
        self._adjacency.setdefault(connection.zone_a, []).append(
            connection.zone_b
        )
        self._adjacency.setdefault(connection.zone_b, []).append(
            connection.zone_a
        )
        key = frozenset((connection.zone_a, connection.zone_b))
        self._connection_index[key] = connection

    def get_zone(self, name: str) -> Zone:
        """Return the Zone instance matching the given name.

        Args:
            name: the zone's name.

        Returns:
            The matching Zone.

        Raises:
            KeyError: if no zone with this name exists.
        """
        return self.zones[name]

    def neighbors(self, zone_name: str) -> list[str]:
        """Return the names of all zones directly connected to zone_name.

        Args:
            zone_name: the zone whose neighbors we want.

        Returns:
            A list of zone names reachable via exactly one connection.
        """
        return list(self._adjacency.get(zone_name, []))

    def has_connection(self, zone_a: str, zone_b: str) -> bool:
        """Return whether a connection already links the two zones.

        The order does not matter: a-b and b-a are the same connection.

        Args:
            zone_a: name of one zone.
            zone_b: name of the other zone.

        Returns:
            True if such a connection exists.
        """
        return frozenset((zone_a, zone_b)) in self._connection_index

    def get_connection(self, zone_a: str, zone_b: str) -> Connection:
        """Return the Connection object linking two given zones.

        Args:
            zone_a: name of one zone.
            zone_b: name of the other zone.

        Returns:
            The matching Connection instance.

        Raises:
            ValueError: if no connection exists between these two zones.
        """
        key = frozenset((zone_a, zone_b))
        if key not in self._connection_index:
            raise ValueError(
                "No connection exists between these two zones."
            )
        return self._connection_index[key]

    @property
    def start_zone(self) -> Zone:
        """Return the unique start_hub zone of the network."""
        for zone in self.zones.values():
            if zone.is_start:
                return zone
        raise ValueError("No start_hub zone found in the network.")

    @property
    def end_zone(self) -> Zone:
        """Return the unique end_hub zone of the network."""
        for zone in self.zones.values():
            if zone.is_end:
                return zone
        raise ValueError("No end_hub zone found in the network.")
