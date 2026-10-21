"""Parser: reads a .txt map file into a Network + list of Drones."""

from models.zone import Zone, ZoneType
from models.network import Network
from models.connection import Connection
from models.drone import Drone


class ParseError(Exception):
    """Raised when the map file is malformed.

    Carries the line number so the error message can point the user
    to exactly where the problem is, as required by the subject.
    """

    def __init__(self, line_number: int, message: str) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(f"Line {line_number}: {message}")


class Parser:
    """Parses a Fly-in map file into a Network and a list of Drones.

    Every syntax or consistency problem raises a ParseError carrying
    the line number and a human-readable cause.
    """

    ZONE_PREFIXES = ("start_hub", "end_hub", "hub")
    ZONE_METADATA_KEYS = ("zone", "color", "max_drones")
    CONNECTION_METADATA_KEYS = ("max_link_capacity",)

    def parse_metadata(
        self, raw: str, line_number: int, allowed_keys: tuple[str, ...]
    ) -> dict[str, str]:
        """Parse a bracketed metadata block into a dict of key/value pairs.

        Example:
            "zone=restricted color=red" -> {"zone": "restricted",
                                            "color": "red"}
            "" -> {}  (no metadata present)

        Args:
            raw: the metadata substring, WITHOUT the surrounding
                brackets. Space-separated "key=value" pairs.
            line_number: the line's position in the file.
            allowed_keys: the only keys accepted in this block.

        Returns:
            A dict mapping each key to its string value.

        Raises:
            ParseError: on a token without "=", an empty key or value,
                an unknown key or a key given twice.
        """
        result: dict[str, str] = {}
        for token in raw.split():
            key, separator, value = token.partition("=")
            if separator == "" or key == "" or value == "" or "=" in value:
                raise ParseError(
                    line_number,
                    f"invalid metadata {token!r} (expected key=value)",
                )
            if key not in allowed_keys:
                raise ParseError(
                    line_number,
                    f"unknown metadata key {key!r} "
                    f"(allowed: {', '.join(allowed_keys)})",
                )
            if key in result:
                raise ParseError(
                    line_number, f"metadata key {key!r} given twice"
                )
            result[key] = value
        return result

    def _split_metadata(self, line: str, line_number: int) -> tuple[str, str]:
        """Split a line into its main part and its bracketed metadata.

        Args:
            line: the stripped line.
            line_number: the line's position in the file.

        Returns:
            (main_part, metadata_without_brackets). The metadata part
            is "" when the line has no brackets.

        Raises:
            ParseError: if the brackets are unbalanced or misplaced.
        """
        if "[" not in line and "]" not in line:
            return line, ""
        if line.count("[") != 1 or line.count("]") != 1:
            raise ParseError(
                line_number, "metadata must be one single [...] block"
            )
        if not line.endswith("]") or line.index("[") > line.index("]"):
            raise ParseError(
                line_number,
                "metadata block [...] must be at the end of the line",
            )
        main_part, rest = line.split("[", 1)
        return main_part, rest[:-1]

    def _parse_positive_int(
        self, value: str, line_number: int, what: str
    ) -> int:
        """Convert a string to a strictly positive integer.

        Args:
            value: the raw string.
            line_number: the line's position in the file.
            what: name of the value, used in the error message.

        Returns:
            The integer value.

        Raises:
            ParseError: if value is not an integer or is <= 0.
        """
        try:
            number = int(value)
        except ValueError:
            raise ParseError(
                line_number, f"{what} must be an integer, got {value!r}"
            ) from None
        if number <= 0:
            raise ParseError(
                line_number, f"{what} must be a positive integer, "
                f"got {number}"
            )
        return number

    def _check_zone_name(self, name: str, line_number: int) -> None:
        """Validate a zone name (no dash, no bracket).

        Args:
            name: the zone name to check.
            line_number: the line's position in the file.

        Raises:
            ParseError: if the name contains a forbidden character.
        """
        for forbidden in ("-", "[", "]"):
            if forbidden in name:
                raise ParseError(
                    line_number,
                    f"zone name {name!r} must not contain {forbidden!r}",
                )

    def parse_zone_line(self, line: str, line_number: int) -> Zone:
        """Parse a zone definition line into a Zone instance.

        Handles all three prefixes (hub:, start_hub:, end_hub:) and
        the optional bracketed metadata block.

        Args:
            line: the raw line, e.g. "hub: roof1 3 4 [zone=restricted]".
            line_number: the line's position in the file.

        Returns:
            A fully constructed Zone instance.

        Raises:
            ParseError: on any syntax or value error.
        """
        main_part, metadata_raw = self._split_metadata(line, line_number)
        metadata = self.parse_metadata(
            metadata_raw, line_number, self.ZONE_METADATA_KEYS
        )

        prefix, _, body = main_part.partition(":")
        elements = body.split()
        if len(elements) != 3:
            raise ParseError(
                line_number,
                f"expected '{prefix}: <name> <x> <y> [metadata]'",
            )
        zone_name = elements[0]
        self._check_zone_name(zone_name, line_number)
        try:
            x = int(elements[1])
            y = int(elements[2])
        except ValueError:
            raise ParseError(
                line_number,
                f"coordinates of {zone_name!r} must be integers, "
                f"got {elements[1]!r} {elements[2]!r}",
            ) from None

        raw_type = metadata.get("zone", "normal")
        try:
            zone_type = ZoneType(raw_type)
        except ValueError:
            allowed = ", ".join(t.value for t in ZoneType)
            raise ParseError(
                line_number,
                f"invalid zone type {raw_type!r} (allowed: {allowed})",
            ) from None

        max_drones = self._parse_positive_int(
            metadata.get("max_drones", "1"), line_number, "max_drones"
        )

        return Zone(
            name=zone_name,
            x=x,
            y=y,
            zone_type=zone_type,
            color=metadata.get("color", None),
            max_drones=max_drones,
            is_start=prefix == "start_hub",
            is_end=prefix == "end_hub",
        )

    def parse_connection_line(
        self, line: str, line_number: int
    ) -> tuple[str, str, int]:
        """Parse a connection definition line into its raw components.

        Returns raw names (not a Connection object) because the
        caller (parse) still needs to validate that both zones exist
        before a real Connection can be safely created.

        Args:
            line: the raw line, e.g. "connection: hub-roof1
                [max_link_capacity=2]".
            line_number: the line's position in the file.

        Returns:
            A (zone_a, zone_b, max_link_capacity) tuple.

        Raises:
            ParseError: on any syntax or value error.
        """
        main_part, metadata_raw = self._split_metadata(line, line_number)
        metadata = self.parse_metadata(
            metadata_raw, line_number, self.CONNECTION_METADATA_KEYS
        )

        elements = main_part.partition(":")[2].split()
        if len(elements) != 1 or elements[0].count("-") != 1:
            raise ParseError(
                line_number,
                "expected 'connection: <zone1>-<zone2> [metadata]'",
            )
        zone_a, zone_b = elements[0].split("-")
        if zone_a == "" or zone_b == "":
            raise ParseError(line_number, "connection has an empty zone")

        max_link_capacity = self._parse_positive_int(
            metadata.get("max_link_capacity", "1"),
            line_number,
            "max_link_capacity",
        )
        return zone_a, zone_b, max_link_capacity

    def _parse_nb_drones(self, line: str, line_number: int) -> int:
        """Parse the "nb_drones: <positive_integer>" line.

        Args:
            line: the stripped line.
            line_number: the line's position in the file.

        Returns:
            The number of drones.

        Raises:
            ParseError: if the line is malformed.
        """
        elements = line.partition(":")[2].split()
        if len(elements) != 1:
            raise ParseError(
                line_number, "expected 'nb_drones: <positive_integer>'"
            )
        return self._parse_positive_int(
            elements[0], line_number, "nb_drones"
        )

    def _add_zone(
        self, network: Network, zone: Zone, line_number: int
    ) -> None:
        """Add a zone after checking uniqueness rules.

        Args:
            network: the network being built.
            zone: the zone just parsed.
            line_number: the line's position in the file.

        Raises:
            ParseError: on a duplicate name or a second start/end hub.
        """
        if zone.name in network.zones:
            raise ParseError(
                line_number, f"duplicate zone name {zone.name!r}"
            )
        for existing in network.zones.values():
            if zone.is_start and existing.is_start:
                raise ParseError(
                    line_number,
                    f"second start_hub (already {existing.name!r})",
                )
            if zone.is_end and existing.is_end:
                raise ParseError(
                    line_number,
                    f"second end_hub (already {existing.name!r})",
                )
        network.add_zone(zone)

    def _add_connection(
        self, network: Network, line: str, line_number: int
    ) -> None:
        """Parse a connection line and add it after consistency checks.

        Args:
            network: the network being built.
            line: the stripped line.
            line_number: the line's position in the file.

        Raises:
            ParseError: on unknown zones, self-loops or duplicates.
        """
        zone_a, zone_b, capacity = self.parse_connection_line(
            line, line_number
        )
        for name in (zone_a, zone_b):
            if name not in network.zones:
                raise ParseError(
                    line_number,
                    f"connection uses undefined zone {name!r} "
                    "(zones must be defined before their connections)",
                )
        if zone_a == zone_b:
            raise ParseError(
                line_number, f"zone {zone_a!r} cannot connect to itself"
            )
        if network.has_connection(zone_a, zone_b):
            raise ParseError(
                line_number,
                f"duplicate connection between {zone_a!r} and {zone_b!r}",
            )
        network.add_connection(Connection(zone_a, zone_b, capacity))

    def parse(self, filepath: str) -> tuple[Network, list[Drone]]:
        """Read a map file and build the Network and the Drones.

        Args:
            filepath: path to the .txt map file.

        Returns:
            The built Network and the list of drones D1..Dn, all placed
            in the start zone.

        Raises:
            ParseError: if the file content is invalid.
            OSError: if the file cannot be opened.
        """
        network = Network()
        nb_drones: int | None = None
        last_line = 0

        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            last_line = line_number

            if line == "" or line.startswith("#"):
                continue

            prefix = line.partition(":")[0].strip()

            if nb_drones is None:
                if prefix != "nb_drones":
                    raise ParseError(
                        line_number,
                        "the first line must be "
                        "'nb_drones: <positive_integer>'",
                    )
                nb_drones = self._parse_nb_drones(line, line_number)
            elif ":" not in line:
                raise ParseError(
                    line_number, f"unrecognized line {line!r}"
                )
            elif prefix == "nb_drones":
                raise ParseError(line_number, "nb_drones defined twice")
            elif prefix in self.ZONE_PREFIXES:
                zone = self.parse_zone_line(line, line_number)
                self._add_zone(network, zone, line_number)
            elif prefix == "connection":
                self._add_connection(network, line, line_number)
            else:
                raise ParseError(
                    line_number, f"unknown line type {prefix!r}"
                )

        if last_line == 0:
            raise ParseError(1, "the file is empty")
        if nb_drones is None:
            raise ParseError(
                last_line, "missing 'nb_drones: <positive_integer>'"
            )
        if not any(z.is_start for z in network.zones.values()):
            raise ParseError(last_line, "missing start_hub definition")
        if not any(z.is_end for z in network.zones.values()):
            raise ParseError(last_line, "missing end_hub definition")

        start_name = network.start_zone.name
        drones: list[Drone] = []
        for i in range(1, nb_drones + 1):
            drones.append(Drone(f"D{i}", start_name))

        return network, drones
