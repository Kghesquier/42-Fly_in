"""Zone: represents a single zone (node) in the drone network."""

from enum import Enum


class ZoneType(str, Enum):
    """The four allowed zone types.

    Inheriting from (str, Enum) lets us compare a ZoneType directly to a
    string, e.g. ZoneType.NORMAL == "normal" -> True. Handy when reading
    the raw string from the parsed file.
    """

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"


class Zone:
    """A single zone in the drone network.

    A Zone only holds its STATIC configuration (name, position, type,
    capacity). It does NOT track which drones are currently inside it —
    that dynamic state belongs to the Simulator, not here.

    Attributes:
        name: Unique identifier of the zone (e.g. "roof1").
        x: X coordinate (integer).
        y: Y coordinate (integer).
        zone_type: One of ZoneType (normal/blocked/restricted/priority).
        color: Optional color string for display purposes, or None.
        max_drones: Maximum number of drones allowed simultaneously.
        is_start: True if this is the unique start_hub zone.
        is_end: True if this is the unique end_hub zone.
    """

    def __init__(
        self,
        name: str,
        x: int,
        y: int,
        zone_type: ZoneType = ZoneType.NORMAL,
        color: str | None = None,
        max_drones: int = 1,
        is_start: bool = False,
        is_end: bool = False,
    ) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.zone_type = zone_type
        self.color = color
        self.is_start = is_start
        self.is_end = is_end

        self.max_drones: float = (
            float("inf") if (is_start or is_end) else max_drones
        )

    @property
    def movement_cost(self) -> int:
        """Return the number of turns required to move INTO this zone.

        Rules from the subject:
          - normal:     1 turn
          - priority:   1 turn
          - restricted: 2 turns
          - blocked:    should never be asked (see can_enter below)

        Returns:
            1 or 2 depending on self.zone_type.
        """
        if self.zone_type == ZoneType.NORMAL:
            return 1
        elif self.zone_type == ZoneType.PRIORITY:
            return 1
        elif self.zone_type == ZoneType.RESTRICTED:
            return 2
        else:
            raise ValueError(
                "Impossible to return the number of turns required to "
                "move into the zone: the zone type might be BLOCKED "
                "or unknown"
            )

    def can_enter(self) -> bool:
        """Return whether a drone is allowed to enter this zone at all.

        A blocked zone can never be entered, regardless of capacity.

        Returns:
            False if zone_type is BLOCKED, True otherwise.
        """
        return self.zone_type != ZoneType.BLOCKED

    def can_accept(self, current_occupants: int) -> bool:
        """Return whether one more drone can enter given current occupancy.

        Args:
            current_occupants: how many drones are currently in this zone
                (this count is tracked and passed in by the Simulator).

        Returns:
            True if adding one more drone would not exceed max_drones
            (or if this zone is start/end, where capacity is unlimited).
        """
        return current_occupants < self.max_drones

    def __repr__(self) -> str:
        return f"Zone({self.name!r}, type={self.zone_type})"
