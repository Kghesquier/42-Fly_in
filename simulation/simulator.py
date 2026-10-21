"""Simulator: moves the drones turn by turn while respecting the rules."""

from dataclasses import dataclass, field

from models.connection import Connection
from models.drone import Drone
from models.network import Network


class SimulationError(Exception):
    """Raised when the simulation cannot go on (e.g. deadlock)."""


@dataclass
class TurnRecord:
    """Everything that happened during one turn (used for display).

    Attributes:
        turn: the turn number (1-based).
        moves: output tokens of the turn, e.g. ["D1-roof1", "D2-a-b"].
        zone_occupancy: drones in (or flying toward) each zone.
        link_usage: drones on each connection during the turn.
        in_transit: drone id -> connection name, for drones still
            flying toward a restricted zone at the end of the turn.
        zone_drones: zone name -> ids of the drones inside it.
        delivered: how many drones have reached the end zone so far.
    """

    turn: int
    moves: list[str]
    zone_occupancy: dict[str, int]
    link_usage: dict[str, int]
    in_transit: dict[str, str]
    zone_drones: dict[str, list[str]]
    delivered: int


@dataclass
class SimulationStats:
    """Secondary metrics of a finished simulation.

    Attributes:
        total_turns: number of turns needed to deliver every drone.
        nb_drones: number of drones.
        total_moves: number of output tokens over the whole simulation.
        arrival_turns: drone id -> turn at which it was delivered.
    """

    total_turns: int
    nb_drones: int
    total_moves: int = 0
    arrival_turns: dict[str, int] = field(default_factory=dict)

    @property
    def average_turns_per_drone(self) -> float:
        """Return the mean delivery turn over all drones."""
        if not self.arrival_turns:
            return 0.0
        return sum(self.arrival_turns.values()) / len(self.arrival_turns)

    @property
    def moves_per_turn(self) -> float:
        """Return the mean number of drone moves per turn."""
        if self.total_turns == 0:
            return 0.0
        return self.total_moves / self.total_turns


class Simulator:
    """Runs the turn-based simulation.

    The Simulator owns all DYNAMIC state: how many drones are in each
    zone and on each connection. Zones and Connections only hold their
    static configuration and answer "can one more drone fit?".

    Attributes:
        network: the map.
        drones: every drone, in id order (each one knows its path).
        turn: number of turns already simulated.
        zone_occupancy: zone name -> drones inside it, or flying
            toward it (a restricted zone place is booked at departure).
        link_usage: connection name -> drones on it during this turn.
    """

    def __init__(self, network: Network, drones: list[Drone]) -> None:
        self.network = network
        self.drones = drones
        self.turn = 0
        self.zone_occupancy: dict[str, int] = {}
        for zone_name in network.zones:
            self.zone_occupancy[zone_name] = 0
        self.zone_occupancy[network.start_zone.name] = len(drones)
        self.link_usage: dict[str, int] = {}
        self.in_transit: dict[str, Connection] = {}
        self.stats = SimulationStats(0, len(drones))

    def is_finished(self) -> bool:
        """Return whether every drone has been delivered."""
        for drone in self.drones:
            if not drone.delivered:
                return False
        return True

    def _use_link(self, connection: Connection) -> None:
        """Count one more drone on a connection for this turn.

        Args:
            connection: the connection being used.
        """
        used = self.link_usage.get(connection.name, 0)
        self.link_usage[connection.name] = used + 1

    def _land(self, drone: Drone, moves: dict[str, str]) -> None:
        """Finish the 2-turn flight of a drone toward a restricted zone.

        Its place in the zone was already booked when it took off, so
        it can always land: a drone never waits on a connection.

        Args:
            drone: a drone currently flying.
            moves: output tokens of the turn (updated here).
        """
        self._use_link(self.in_transit[drone.drone_id])
        drone.advance_turn()
        del self.in_transit[drone.drone_id]
        moves[drone.drone_id] = f"{drone.drone_id}-{drone.current_zone}"
        self._check_delivered(drone)

    def _try_move(self, drone: Drone, moves: dict[str, str]) -> bool:
        """Move a drone one zone forward on its path, if possible.

        Args:
            drone: a drone standing in a zone.
            moves: output tokens of the turn (updated here).

        Returns:
            True if the drone moved, False if it has to wait.
        """
        current = drone.current_zone
        next_name = drone.next_zone()
        if current is None or next_name is None:
            return False
        next_zone = self.network.get_zone(next_name)
        connection = self.network.get_connection(current, next_name)

        # 1. Is there room in the next zone and on the connection?
        if not next_zone.can_accept(self.zone_occupancy[next_name]):
            return False
        if not connection.can_traverse(
            self.link_usage.get(connection.name, 0)
        ):
            return False

        # 2. Leave the current zone (frees the place this same turn)
        #    and book the place in the next zone.
        self.zone_occupancy[current] -= 1
        self.zone_occupancy[next_name] += 1
        self._use_link(connection)
        drone.path_index += 1

        # 3. Move: 1 turn for normal/priority, 2 turns for restricted.
        drone.start_move(next_name, next_zone.movement_cost)
        drone.advance_turn()
        if drone.is_moving():
            self.in_transit[drone.drone_id] = connection
            moves[drone.drone_id] = f"{drone.drone_id}-{connection.name}"
        else:
            moves[drone.drone_id] = f"{drone.drone_id}-{next_name}"
            self._check_delivered(drone)
        return True

    def _check_delivered(self, drone: Drone) -> None:
        """Mark the drone as delivered if it stands in the end zone.

        Args:
            drone: a drone that just arrived in a zone.
        """
        if drone.current_zone == self.network.end_zone.name:
            drone.mark_delivered()
            self.stats.arrival_turns[drone.drone_id] = self.turn

    def step(self) -> TurnRecord:
        """Simulate one turn.

        1. Drones flying toward a restricted zone land.
        2. The other drones try to move forward, D1 first. D1 left
           the start first, so it is in front: when it moves it frees
           its place for the drone behind it during the same turn.

        Returns:
            The TurnRecord describing this turn.

        Raises:
            SimulationError: if no drone can move anymore (deadlock).
        """
        self.turn += 1
        self.link_usage = {}
        moves: dict[str, str] = {}

        for drone in self.drones:
            if drone.is_moving():
                self._land(drone, moves)

        for drone in self.drones:
            if drone.delivered or drone.drone_id in moves:
                continue
            self._try_move(drone, moves)

        if not moves:
            raise SimulationError(
                f"turn {self.turn}: no drone can move (deadlock)"
            )

        ordered_moves: list[str] = []
        for drone in self.drones:
            if drone.drone_id in moves:
                ordered_moves.append(moves[drone.drone_id])
        self.stats.total_moves += len(ordered_moves)
        self.stats.total_turns = self.turn
        return self._record(ordered_moves)

    def _record(self, moves: list[str]) -> TurnRecord:
        """Build a snapshot of the current state.

        Args:
            moves: output tokens of the turn.

        Returns:
            A TurnRecord (copies, so later turns do not modify it).
        """
        zone_drones: dict[str, list[str]] = {}
        for zone_name in self.network.zones:
            zone_drones[zone_name] = []
        delivered = 0
        for drone in self.drones:
            if drone.delivered:
                delivered += 1
            elif drone.current_zone is not None:
                zone_drones[drone.current_zone].append(drone.drone_id)

        in_transit: dict[str, str] = {}
        for drone_id, connection in self.in_transit.items():
            in_transit[drone_id] = connection.name

        return TurnRecord(
            turn=self.turn,
            moves=moves,
            zone_occupancy=dict(self.zone_occupancy),
            link_usage=dict(self.link_usage),
            in_transit=in_transit,
            zone_drones=zone_drones,
            delivered=delivered,
        )
