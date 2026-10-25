"""life.py -- Conway's Game of Life on a 13x8 toroidal board.

Pure Python, standard library only, no hardware imports: this module is
the simulation engine for q_life.py, which pushes the frames to the
Arduino Uno Q's LED matrix (or to the terminal).

The board is 13 cells wide by 8 tall, matching the matrix, and wraps
around at every edge (a torus). On a board this small wrapping is not a
detail -- most interesting patterns quickly reach an edge, and a torus
keeps them in play instead of killing them against a wall.

Rules (classic B3/S23):

* a live cell with 2 or 3 live neighbors survives,
* a dead cell with exactly 3 live neighbors is born,
* every other cell dies or stays dead.

Cells are (x, y) pairs, x growing right (0..12), y growing down (0..7).
Coordinates outside the board wrap modulo the board size, both when a
grid is built and when neighbors are counted.
"""

import random

COLS = 13
ROWS = 8

DEFAULT_MAX_GENERATIONS = 150
DEFAULT_MIN_GENERATIONS = 6
SOUP_DENSITY = 0.2


class Grid:
    """One generation: an immutable set of live cells on the torus."""

    def __init__(self, cells=()):
        self.cells = frozenset((x % COLS, y % ROWS) for x, y in cells)

    @property
    def population(self):
        return len(self.cells)

    def key(self):
        """A hashable snapshot of the state, for cycle detection."""
        return self.cells

    def step(self):
        """Return the next generation under B3/S23 on the torus."""
        counts = {}
        for x, y in self.cells:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    neighbor = ((x + dx) % COLS, (y + dy) % ROWS)
                    counts[neighbor] = counts.get(neighbor, 0) + 1
        return Grid(
            cell
            for cell, n in counts.items()
            if n == 3 or (n == 2 and cell in self.cells)
        )

    def __eq__(self, other):
        return isinstance(other, Grid) and self.cells == other.cells

    def __hash__(self):
        return hash(self.cells)

    def __repr__(self):
        return f"Grid({sorted(self.cells)!r})"

    def __str__(self):
        return "\n".join(
            "".join("#" if (x, y) in self.cells else "." for x in range(COLS))
            for y in range(ROWS)
        )


# ---------------------------------------------------------------------------
# Pattern library. Each entry is a list of (x, y) cells in the pattern's
# own small bounding box; placement (centering / composing) happens in
# _build_patterns() below.
# ---------------------------------------------------------------------------

GLIDER = [(1, 0), (2, 1), (0, 2), (1, 2), (2, 2)]

LWSS = [
    (1, 0), (4, 0),
    (0, 1),
    (0, 2), (4, 2),
    (0, 3), (1, 3), (2, 3), (3, 3),
]

R_PENTOMINO = [(1, 0), (2, 0), (0, 1), (1, 1), (1, 2)]

DIEHARD = [(6, 0), (0, 1), (1, 1), (1, 2), (5, 2), (6, 2), (7, 2)]

ACORN = [(1, 0), (3, 1), (0, 2), (1, 2), (4, 2), (5, 2), (6, 2)]

BLINKER = [(0, 0), (1, 0), (2, 0)]

TOAD = [(1, 0), (2, 0), (3, 0), (0, 1), (1, 1), (2, 1)]

BEACON = [
    (0, 0), (1, 0), (0, 1), (1, 1),
    (2, 2), (3, 2), (2, 3), (3, 3),
]

BLOCK = [(0, 0), (1, 0), (0, 1), (1, 1)]

BEEHIVE = [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (2, 2)]

LOAF = [(1, 0), (2, 0), (0, 1), (3, 1), (1, 2), (3, 2), (2, 3)]

BOAT = [(0, 0), (1, 0), (0, 1), (2, 1), (1, 2)]

TUB = [(1, 0), (0, 1), (2, 1), (1, 2)]


def _shift(cells, dx, dy):
    return [(x + dx, y + dy) for x, y in cells]


def _centered(cells):
    """Translate a pattern so its bounding box sits at the board's center."""
    xs = [x for x, _ in cells]
    ys = [y for _, y in cells]
    dx = (COLS - (max(xs) - min(xs) + 1)) // 2 - min(xs)
    dy = (ROWS - (max(ys) - min(ys) + 1)) // 2 - min(ys)
    return _shift(cells, dx, dy)


# Composed sets. The placements were machine-searched and are pinned by
# the tests: the oscillators keep a joint period of 2 side by side, and
# the still lifes simply sit there. (On a 13x8 torus this is fussier than
# it looks -- patterns interact across the wrap seams if they sit too
# close, so do not nudge these offsets casually.)
OSCILLATORS = (
    _shift(BLINKER, 10, 5) + _shift(TOAD, 5, 5) + _shift(BEACON, 0, 0)
)

STILL_LIFES = (
    _shift(BLOCK, 12, 1)
    + _shift(BEEHIVE, 6, 7)
    + _shift(LOAF, 8, 4)
    + _shift(BOAT, 2, 1)
    + _shift(TUB, 4, 5)
)


def soup_cells(seed, density=SOUP_DENSITY):
    """A random starting board from a seeded RNG (reproducible rounds)."""
    rng = random.Random(seed)
    return [
        (x, y)
        for y in range(ROWS)
        for x in range(COLS)
        if rng.random() < density
    ]


def build_patterns(seed=0):
    """The ordered pattern cycle: a list of (name, starting Grid).

    ``seed`` feeds only the random-soup round, so a given seed always
    produces the same show.
    """
    return [
        ("Glider", Grid(_centered(GLIDER))),
        ("Lightweight spaceship", Grid(_centered(LWSS))),
        ("R-pentomino", Grid(_centered(R_PENTOMINO))),
        ("Diehard", Grid(_centered(DIEHARD))),
        ("Acorn", Grid(_centered(ACORN))),
        ("Oscillators", Grid(OSCILLATORS)),
        ("Still lifes", Grid(STILL_LIFES)),
        ("Random soup", Grid(soup_cells(seed))),
    ]


class Cycler:
    """Plays the pattern library forever, one pattern at a time.

    A pattern's run ends when the board empties, when a state repeats
    (a still life or an oscillator cycle), or when the generation cap
    is reached -- but never before ``min_generations`` frames have been
    shown, so even a motionless still life gets a moment on stage.

    ``patterns`` may inject a custom [(name, cells), ...] sequence
    (the tests use it); by default the library from build_patterns()
    is used and the soup is re-seeded on every lap.

    The generation bounds must satisfy
    ``1 <= min_generations <= max_generations``. The minimum is a floor
    on how long a pattern stays up, not an override of the cap: with
    contradictory bounds (a minimum above the maximum) the run would
    silently exceed the requested maximum, so they are rejected here
    for every caller, not just the CLI.
    """

    def __init__(
        self,
        patterns=None,
        max_generations=DEFAULT_MAX_GENERATIONS,
        min_generations=DEFAULT_MIN_GENERATIONS,
        seed=0,
    ):
        if max_generations < 1:
            raise ValueError(
                f"max_generations must be at least 1, got {max_generations!r}"
            )
        if min_generations < 1:
            raise ValueError(
                f"min_generations must be at least 1, got {min_generations!r}"
            )
        if min_generations > max_generations:
            raise ValueError(
                f"min_generations ({min_generations!r}) must not exceed "
                f"max_generations ({max_generations!r})"
            )
        self._fixed = patterns
        self.max_generations = max_generations
        self.min_generations = min_generations
        self.seed = seed

    def _lap(self, lap_number):
        if self._fixed is not None:
            return [(name, Grid(cells)) for name, cells in self._fixed]
        return build_patterns(self.seed + lap_number)

    def pattern_names(self):
        return [name for name, _ in self._lap(0)]

    def frames(self):
        """Yield (pattern name, Grid, generation) forever."""
        lap = 0
        while True:
            for name, grid in self._lap(lap):
                yield from self._run_pattern(name, grid)
            lap += 1

    def _run_pattern(self, name, grid):
        seen = set()
        generation = 0
        while True:
            yield name, grid, generation
            seen.add(grid.key())
            following = grid.step()
            generation += 1
            if generation >= self.min_generations and (
                following.population == 0
                or following.key() in seen
                or generation >= self.max_generations
            ):
                return
            grid = following
