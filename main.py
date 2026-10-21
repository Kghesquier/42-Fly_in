#!/usr/bin/env python3
"""Entry point of the Fly-in simulation.

Usage:
    python3 main.py <map_file> [--visual] [--no-color]
"""

import argparse
import sys

from algorithms.scheduler import NoPathError, Scheduler
from parsing.parser import ParseError, Parser
from simulation.simulator import SimulationError, Simulator
from visualization.visualizer import Visualizer


class FlyInApp:
    """Wires the parser, scheduler, simulator and visualizer together."""

    def build_argument_parser(self) -> argparse.ArgumentParser:
        """Create the command-line interface.

        Returns:
            The configured ArgumentParser.
        """
        parser = argparse.ArgumentParser(
            description="Route a fleet of drones from start to end "
            "in as few turns as possible."
        )
        parser.add_argument("map_file", help="path to the map .txt file")
        parser.add_argument(
            "-v", "--visual",
            action="store_true",
            help="show the map, the zone states after each turn "
            "and a final summary",
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="disable ANSI colors",
        )
        return parser

    def run(self, argv: list[str]) -> int:
        """Run the whole program.

        Args:
            argv: command-line arguments (without the program name).

        Returns:
            The process exit code (0 on success, 1 on error).
        """
        args = self.build_argument_parser().parse_args(argv)
        use_color = not args.no_color and sys.stdout.isatty()
        try:
            network, drones = Parser().parse(args.map_file)
            Scheduler(network).assign_paths(drones)
            simulator = Simulator(network, drones)
            visualizer = Visualizer(network, use_color, args.visual)

            while not simulator.is_finished():
                record = simulator.step()
                visualizer.show_turn(record)
            visualizer.show_summary(simulator.stats)
        except ParseError as error:
            print(f"Parse error: {error}", file=sys.stderr)
            return 1
        except (NoPathError, SimulationError) as error:
            print(f"Simulation error: {error}", file=sys.stderr)
            return 1
        except UnicodeDecodeError:
            print(
                f"Error: {args.map_file!r} is not a valid text file",
                file=sys.stderr,
            )
            return 1
        except OSError as error:
            print(
                f"Error: cannot read {args.map_file!r}: {error.strerror}",
                file=sys.stderr,
            )
            return 1
        return 0


def main() -> None:
    """Program entry point."""
    try:
        sys.exit(FlyInApp().run(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        sys.exit(130)


if __name__ == "__main__":
    main()
