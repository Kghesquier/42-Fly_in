"""Visualizer: colored terminal output of the simulation."""

from simulation.simulator import SimulationStats, TurnRecord
from models.network import Network
from models.zone import Zone, ZoneType


class ColorPalette:
    """Translates zone color names into ANSI terminal escape codes.

    The subject accepts any single-word color. Known names get a
    256-color code; unknown names fall back to the default terminal
    color (no crash). "rainbow" is drawn with one color per letter.
    """

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CODES: dict[str, int] = {
        "black": 240, "gray": 245, "grey": 245, "white": 255,
        "red": 196, "darkred": 88, "maroon": 52, "crimson": 161,
        "orange": 208, "brown": 130, "yellow": 226, "gold": 220,
        "green": 34, "lime": 118, "cyan": 51, "blue": 33,
        "purple": 129, "violet": 177, "magenta": 201, "pink": 213,
    }
    RAINBOW = (196, 208, 226, 46, 33, 129)

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def paint(self, text: str, color: str | None) -> str:
        """Color a piece of text.

        Args:
            text: the text to color.
            color: a color name from the map, or None.

        Returns:
            The text wrapped in ANSI codes (unchanged if colors are
            disabled or the color is unknown).
        """
        if not self.enabled or color is None:
            return text
        name = color.lower()
        if name == "rainbow":
            return "".join(
                f"\033[38;5;{self.RAINBOW[i % len(self.RAINBOW)]}m{char}"
                for i, char in enumerate(text)
            ) + self.RESET
        if name not in self.CODES:
            return text
        return f"\033[38;5;{self.CODES[name]}m{text}{self.RESET}"

    def style(self, text: str, code: str) -> str:
        """Apply a style (bold, dim) to text.

        Args:
            text: the text.
            code: one of BOLD or DIM.

        Returns:
            The styled text, or the raw text if colors are disabled.
        """
        if not self.enabled:
            return text
        return f"{code}{text}{self.RESET}"


class Visualizer:
    """Prints the simulation in the terminal.

    Default mode prints exactly one line per turn in the required
    format ("D1-roof1 D2-corridorA"), each destination painted with
    the color of its zone. The optional board mode adds, after every
    turn, the state of each zone (occupancy / capacity and drone ids)
    and the drones still flying toward restricted zones.

    Attributes:
        network: the map being displayed.
        palette: the ColorPalette in use.
        show_board: whether to print the zone board after each turn.
    """

    TYPE_SYMBOLS: dict[ZoneType, str] = {
        ZoneType.NORMAL: " ",
        ZoneType.PRIORITY: "+",
        ZoneType.RESTRICTED: "!",
        ZoneType.BLOCKED: "x",
    }

    def __init__(
        self, network: Network, use_color: bool, show_board: bool
    ) -> None:
        self.network = network
        self.palette = ColorPalette(use_color)
        self.show_board = show_board
        self._name_width = max(len(name) for name in network.zones)

    def _zone_label(self, zone: Zone) -> str:
        """Return the zone name padded and painted with its color."""
        padded = zone.name.ljust(self._name_width)
        return self.palette.paint(padded, zone.color)

    def format_moves(self, record: TurnRecord) -> str:
        """Format the moves of a turn in the required output format.

        Args:
            record: the turn to format.

        Returns:
            The line, e.g. "D1-roof1 D2-hub-roof2", with colors.
        """
        parts: list[str] = []
        for token in record.moves:
            drone_id, _, target = token.partition("-")
            if drone_id in record.in_transit:
                destination = self.palette.style(target, ColorPalette.DIM)
            else:
                color = self.network.get_zone(target).color
                destination = self.palette.paint(target, color)
            drone = self.palette.style(drone_id, ColorPalette.BOLD)
            parts.append(f"{drone}-{destination}")
        return " ".join(parts)

    def show_turn(self, record: TurnRecord) -> None:
        """Print one turn (and the board if enabled).

        Args:
            record: the turn to display.
        """
        line = self.format_moves(record)
        if not self.show_board:
            print(line)
            return
        turn = self.palette.style(f"Turn {record.turn:>3}", ColorPalette.BOLD)
        print(f"{turn} | {line}")
        self._show_board(record)

    def _show_board(self, record: TurnRecord) -> None:
        """Print the state of every zone after a turn.

        Args:
            record: the turn to display.
        """
        for zone in self.network.zones.values():
            drones = record.zone_drones[zone.name]
            if zone.is_end:
                drones_text = f"{record.delivered} delivered"
                gauge = ""
            else:
                count = record.zone_occupancy[zone.name]
                if zone.is_start:
                    gauge = f"{count:>3}    "
                else:
                    gauge = f"{count:>3}/{int(zone.max_drones):<3}"
                drones_text = " ".join(drones)
            if not drones and not zone.is_end and not zone.is_start:
                continue
            print(
                f"      {self.TYPE_SYMBOLS[zone.zone_type]} "
                f"{self._zone_label(zone)} {gauge} {drones_text}"
            )
        for drone_id, connection_name in record.in_transit.items():
            arrow = self.palette.style("~>", ColorPalette.DIM)
            print(f"      {arrow} {drone_id} flying on {connection_name}")
        for line in self.connection_lines(record, only_used=True):
            print(f"      {line}")
        print()

    def connection_lines(
        self, record: TurnRecord, only_used: bool = False
    ) -> list[str]:
        """Describe the usage of every connection during a turn.

        Args:
            record: the turn to describe.
            only_used: if True, skip the connections nobody used.

        Returns:
            Lines like "Connection start-a: 1/2 capacity used".
        """
        lines: list[str] = []
        for connection in self.network.connections:
            used = record.link_usage.get(connection.name, 0)
            if only_used and used == 0:
                continue
            lines.append(
                f"Connection {connection.name}: "
                f"{used}/{connection.max_link_capacity} capacity used"
            )
        return lines

    def show_summary(self, stats: SimulationStats) -> None:
        """Print the final metrics (board mode only).

        Args:
            stats: the metrics of the finished simulation.
        """
        if not self.show_board:
            return
        print(self.palette.style("=== Summary ===", ColorPalette.BOLD))
        print(f"  total turns           : {stats.total_turns}")
        print(f"  drones delivered      : {stats.nb_drones}")
        print(f"  total moves           : {stats.total_moves}")
        print(f"  moves per turn        : {stats.moves_per_turn:.2f}")
        print(
            f"  avg turns per drone   : "
            f"{stats.average_turns_per_drone:.2f}"
        )
