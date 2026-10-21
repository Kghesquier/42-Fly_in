"""Independent checker of a simulation output.

It replays the printed lines ("D1-a D2-a-b ...") on the Network and
checks every rule of the subject WITHOUT using the Simulator, so a bug
in the Simulator cannot hide itself.
"""

from models.network import Network
from models.zone import ZoneType


class OutputValidator:
    """Replays an output and raises AssertionError on any violation."""

    def __init__(self, network: Network, nb_drones: int) -> None:
        self.network = network
        self.nb_drones = nb_drones
        self.connections = {c.name: c for c in network.connections}

    def validate(self, lines: list[str]) -> None:
        """Check a whole simulation output.

        Args:
            lines: one string per turn.

        Raises:
            AssertionError: on the first rule violation.
        """
        start = self.network.start_zone.name
        end = self.network.end_zone.name
        position: dict[str, str] = {
            f"D{i}": start for i in range(1, self.nb_drones + 1)
        }
        flying: dict[str, tuple[str, str]] = {}
        delivered: set[str] = set()

        for turn, line in enumerate(lines, start=1):
            link_use: dict[str, int] = {}
            for drone_id, (conn_name, _) in flying.items():
                link_use[conn_name] = link_use.get(conn_name, 0) + 1
            seen: set[str] = set()
            landing = dict(flying)
            flying = {}

            for token in line.split():
                drone_id, _, target = token.partition("-")
                assert drone_id in position, f"t{turn}: unknown {drone_id}"
                assert drone_id not in delivered, f"t{turn}: {token}"
                assert drone_id not in seen, f"t{turn}: {drone_id} twice"
                seen.add(drone_id)

                if drone_id in landing:
                    _, dest = landing.pop(drone_id)
                    assert target == dest, f"t{turn}: {token} != {dest}"
                    position[drone_id] = dest
                    continue

                origin = position[drone_id]
                if target in self.connections:
                    conn = self.connections[target]
                    assert conn.connects(origin), f"t{turn}: {token}"
                    dest = conn.other_end(origin)
                    zone = self.network.get_zone(dest)
                    assert zone.zone_type == ZoneType.RESTRICTED
                    flying[drone_id] = (conn.name, dest)
                    position[drone_id] = ""
                else:
                    zone = self.network.get_zone(target)
                    assert zone.zone_type in (
                        ZoneType.NORMAL, ZoneType.PRIORITY
                    ), f"t{turn}: {token} needs 1 turn but is {zone}"
                    conn = self.network.get_connection(origin, target)
                    position[drone_id] = target
                link_use[conn.name] = link_use.get(conn.name, 0) + 1

            assert not landing, f"t{turn}: {landing} waited on a link"
            for name, used in link_use.items():
                cap = self.connections[name].max_link_capacity
                assert used <= cap, f"t{turn}: link {name} {used}/{cap}"

            occupancy: dict[str, int] = {}
            for drone_id, zone_name in position.items():
                if zone_name == end:
                    delivered.add(drone_id)
                elif zone_name not in ("", start):
                    occupancy[zone_name] = occupancy.get(zone_name, 0) + 1
            for zone_name, count in occupancy.items():
                zone = self.network.get_zone(zone_name)
                assert zone.can_enter(), f"t{turn}: in blocked {zone_name}"
                assert count <= zone.max_drones, (
                    f"t{turn}: zone {zone_name} {count}/{zone.max_drones}"
                )

        assert not flying, "simulation ended with drones in flight"
        assert len(delivered) == self.nb_drones, "not all drones delivered"
