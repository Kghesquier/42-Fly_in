*This project has been created as part of the 42 curriculum by kghesqui.*

# Fly-in

## Description

Fly-in is a turn-based drone routing simulator written in Python. A map
describes a graph of **zones** (nodes) linked by **connections** (edges).
All drones start in the `start_hub` zone and must reach the `end_hub` zone
in **as few turns as possible**, while respecting:

- zone capacities (`max_drones`, default 1; unlimited on start/end),
- connection capacities (`max_link_capacity`, default 1),
- movement costs that depend on the destination zone type:
  `normal` = 1 turn, `priority` = 1 turn (preferred),
  `restricted` = 2 turns (the drone flies on the connection and **must**
  land at the next turn), `blocked` = never enterable.

The program parses the map, gives a path to every drone, runs the
simulation turn by turn while checking every capacity, and prints one line
per turn:

```
D1-roof1 D2-corridorA
D1-roof2 D2-tunnelB
D1-goal D2-goal
```

`D<ID>-<zone>` means the drone reached that zone this turn;
`D<ID>-<zoneA>-<zoneB>` means it is still flying on that connection toward
a restricted zone. Drones that do not move are omitted.

The whole project is object-oriented, fully type-hinted (`mypy --strict`
clean), `flake8` clean, and uses no graph library: the graph and
Dijkstra are implemented by hand.

## Instructions

Requirements: Python 3.10 or later.

```bash
make install                 # create ./venv and install flake8, mypy, pytest
make run                     # run the default map (easy/01_linear_path)
make run MAP=maps/hard/02_capacity_hell.txt
make visual MAP=maps/medium/02_circular_loop.txt   # with the zone board
make debug MAP=...           # run under pdb
make test                    # pytest
make lint                    # flake8 + mypy (subject flags)
make lint-strict             # flake8 + mypy --strict
make clean                   # remove caches
```

Or directly:

```bash
./main.py <map_file> [--visual] [--no-color]
```

| Option        | Effect                                                     |
|---------------|------------------------------------------------------------|
| `--visual/-v` | state of every zone after each turn, final summary          |
| `--no-color`  | plain text (colors are also disabled when piping output)   |

Errors (invalid map, missing file, unreachable goal...) are printed on
stderr as one clear message with the line number, and the exit code is 1.
The program never shows a Python traceback.

## Project structure

```
main.py                     FlyInApp: command line, error handling, main loop
models/zone.py              Zone, ZoneType (static config: type, capacity, color)
models/connection.py        Connection (static config: ends, link capacity)
models/network.py           Network: the graph (adjacency list, lookups)
models/drone.py             Drone: its own position / in-flight state
parsing/parser.py           Parser, ParseError (every validation rule)
algorithms/path_finder.py   PathFinder: Dijkstra, several paths
algorithms/scheduler.py     Scheduler: gives a path to each drone
simulation/simulator.py     Simulator, TurnRecord, SimulationStats
visualization/visualizer.py Visualizer, ColorPalette (ANSI colors)
tests/                      pytest suite + an independent output validator
maps/                       subject maps, edge_cases/ and invalid/ maps
```

Design rule: `Zone` and `Connection` only hold **static** configuration.
The **dynamic** state (how many drones are in a zone / on a link) is owned
by the `Simulator`, which asks `zone.can_accept(n)` /
`connection.can_traverse(n)` before every move. The `Scheduler` chooses
the path of each drone, the `Simulator` moves the drones and checks the
rules, the `Visualizer` displays.

## Algorithm explanation

The algorithm has three simple steps.

### 1. Find a few paths (Dijkstra)

`PathFinder.shortest_path` is a classic Dijkstra: it repeatedly takes the
cheapest unvisited zone and updates ("relaxes") its neighbors. Entering a
zone costs its movement cost (1, or 2 for `restricted`); `blocked` zones
are skipped. A `priority` zone costs 0.9 instead of 1, so when two paths
are equally long, the one through priority zones wins.

`PathFinder.find_paths` runs Dijkstra up to 5 times. After each run, the
zones of the path found get a big penalty (+100), so the next run looks
for a path through other zones. It stops when the same path comes back
(no real alternative). Result: the shortest path plus some alternative
paths (disjoint when the map allows it).

If no path exists (disconnected graph, blocked zones), a clear error is
printed before the simulation starts.

### 2. Spread the drones over the paths (Scheduler)

Like choosing a queue at the supermarket: for each path we estimate

```
estimate = path_cost + number_of_drones_already_assigned_to_it
```

(each drone in front of you delays you by about one turn). Drones are
assigned one by one to the path with the smallest estimate. The first
drones take the shortest path; when it gets crowded, the next drones use
the alternative paths.

### 3. Move the drones turn by turn (Simulator)

Each drone follows its own path (`drone.path`). Every turn:

1. drones flying toward a restricted zone land (they cannot wait on a
   connection);
2. every other drone, D1 first, tries to move one zone forward. It moves
   only if the next zone has room and the connection has room this turn;
   otherwise it **waits** in place. Leaving a zone frees the place
   immediately for the drone behind it (D1 is always in front, so it
   moves first).

For a restricted zone, the place in the zone is booked when the drone
takes off, so it is guaranteed to land at the next turn.

Capacities are always checked with `zone.can_accept(n)` and
`connection.can_traverse(n)` before a move, so the output never breaks a
rule. If no drone can move during a turn, the simulation stops with a
clear "deadlock" error instead of looping forever.

### Complexity and trade-offs

- `Z` zones, `E` connections, `D` drones, `T` turns.
- One Dijkstra (minimum found with a linear scan): `O(Z^2 + E)`.
  At most 5 runs, done once at the beginning.
- Path assignment: `O(D * P)` with `P <= 5` paths.
- Simulation: `O(T * D)` (each turn, each drone tries one move; zone and
  connection lookups are dictionaries, `O(1)`).
- Memory: `O(Z + E + D * L)` (`L` = path length, each drone keeps its
  path).
- Paths are computed once and **cached** in each drone; nothing is
  recomputed during the simulation.
- Trade-off: the paths are fixed in advance. A drone never changes its
  path during the simulation, even if another path becomes free. This is
  simple and predictable but not optimal on very crowded maps.

### Results

| Map                        | Drones | Turns |
|----------------------------|-------:|------:|
| easy/01_linear_path        | 2      | 4     |
| easy/02_simple_fork        | 4      | 4     |
| easy/03_basic_capacity     | 4      | 4     |
| medium/01_dead_end_trap    | 5      | 8     |
| medium/02_circular_loop    | 6      | 15    |
| medium/03_priority_puzzle  | 5      | 7     |
| hard/01_maze_nightmare     | 8      | 13    |
| hard/02_capacity_hell      | 12     | 16    |
| hard/03_ultimate_challenge | 15     | 29    |
| challenger/impossible_dream| 25     | 49    |

## Visual representation

- **Colored output** (default in a terminal): each destination zone is
  printed in the `color=` given in the map (any single-word color; known
  names are mapped to 256-color ANSI codes, unknown names stay uncolored,
  `rainbow` is drawn letter by letter). Drone ids are bold, connections of
  drones still in flight are dimmed. The text is exactly the required
  format, so colors never break the output.
- **`--visual` board**: after every turn, the list of non-empty zones
  (prefixed by `+` priority, `!` restricted) with
  `occupancy/capacity` and the drones inside, the drones flying on a
  connection (`~> D3 flying on loop_b-exit_point`), and the number of
  delivered drones. It makes bottlenecks, waiting queues and 2-turn
  restricted moves visible at a glance.
- **Summary** (`--visual`): total turns, moves per turn and average
  delivery turn per drone (secondary metrics of the subject).

## Example

Input (`maps/easy/02_simple_fork.txt`):

```
nb_drones: 4
start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]
connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output (`./main.py maps/easy/02_simple_fork.txt`):

```
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

Restricted zone (`maps/edge_cases/single_drone.txt`, `b` is restricted):

```
D1-a
D1-a-b
D1-b
D1-goal
```

Error example:

```
$ ./main.py maps/invalid/invalid_zone_type.txt
Parse error: Line 3: invalid zone type 'lava' (allowed: normal, blocked, restricted, priority)
```

## Resources

- Dijkstra's algorithm — https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm
- Red Blob Games, *Introduction to graph search*:
  https://www.redblobgames.com/pathfinding/a-star/introduction.html
- Python docs: `dataclasses`, `enum`, `argparse` —
  https://docs.python.org/3/library/
- mypy docs — https://mypy.readthedocs.io/ ; flake8 —
  https://flake8.pycqa.org/
- ANSI escape codes — https://en.wikipedia.org/wiki/ANSI_escape_code

### How AI was used

AI assitant Claude was used in this project. Due to some personal reason that I can explain(feel free to ask) I had to work during small sessions and sometimes I couldn't work for several days. It was hard for me to manage all the milestone 3 projects because I usually work during big session focusing on one project. As it was hard to remember what I had done on my previous coding session, what was left to do, and sometimes even what was the project about I used claude to help me plannify and keep a trace of my advencements. Sometimes it even help me to gain some time giving me the global structure of the code and helping me to generate doctstrings. All the code was handwritted and everything that claude produced(docstrings, README...) was double checked by myself. I know it's not an optimal way to work on the 42 projects but I had no choice if I didn't whant to get blackholed.

Claude was also used to do some complemetary tests on the project and to write the additional pytest files. I check everything before submission with peers but I like to ask claude to do tests just in case.
