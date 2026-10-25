"""Tests for life.py -- they prove the rules, not just the plumbing.

Run from the repo root:  python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

import life
from life import Grid


def stepped(grid, n):
    for _ in range(n):
        grid = grid.step()
    return grid


def translated(cells, dx, dy):
    return Grid([(x + dx, y + dy) for x, y in cells])


class RulesTests(unittest.TestCase):
    def test_block_is_stable(self):
        block = Grid(life.BLOCK)
        self.assertEqual(block.step(), block)

    def test_blinker_has_period_two(self):
        blinker = Grid(life.BLINKER)
        once = blinker.step()
        self.assertNotEqual(once, blinker)
        # The blinker's other phase is the vertical bar.
        self.assertEqual(once, Grid([(1, -1), (1, 0), (1, 1)]))
        self.assertEqual(once.step(), blinker)

    def test_glider_translates_by_one_one_after_four_generations(self):
        glider = Grid(life.GLIDER)
        self.assertEqual(stepped(glider, 4), translated(life.GLIDER, 1, 1))

    def test_glider_wraps_across_the_corner(self):
        # Park the glider so its 4-generation walk crosses the right and
        # bottom edges at once; on the torus it must come out the other
        # side translated by (+1, +1), modulo the board.
        start = [(x + 12, y + 6) for x, y in life.GLIDER]
        expected = [(x + 13, y + 7) for x, y in life.GLIDER]
        self.assertEqual(stepped(Grid(start), 4), Grid(expected))

    def test_lwss_translates_two_columns_after_four_generations(self):
        ship = Grid(life.LWSS)
        # This orientation of the LWSS travels in the -x direction.
        self.assertEqual(stepped(ship, 4), translated(life.LWSS, -2, 0))

    def test_lone_cell_dies(self):
        self.assertEqual(Grid([(5, 3)]).step().population, 0)

    def test_overcrowded_cell_dies(self):
        # The center of a plus has four live neighbors: overcrowding.
        plus = Grid([(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)])
        self.assertNotIn((1, 1), plus.step().cells)

    def test_birth_needs_exactly_three(self):
        # An L-tromino's empty corner has exactly three neighbors and is
        # born, completing the block; the tromino's own cells survive.
        corner = Grid([(0, 0), (1, 0), (0, 1)])
        self.assertEqual(corner.step(), Grid(life.BLOCK))


class LibraryTests(unittest.TestCase):
    EXPECTED_NAMES = [
        "Glider",
        "Lightweight spaceship",
        "R-pentomino",
        "Diehard",
        "Acorn",
        "Oscillators",
        "Still lifes",
        "Random soup",
    ]

    def test_library_order_and_names(self):
        names = [name for name, _ in life.build_patterns(0)]
        self.assertEqual(names, self.EXPECTED_NAMES)

    def test_every_pattern_places_in_bounds_and_steps(self):
        for name, grid in life.build_patterns(0):
            with self.subTest(pattern=name):
                self.assertTrue(
                    all(0 <= x < life.COLS and 0 <= y < life.ROWS
                        for x, y in grid.cells)
                )
                self.assertGreater(grid.population, 0)
                following = grid.step()
                self.assertIsInstance(following, Grid)

    def test_oscillator_set_has_period_two(self):
        oscillators = Grid(life.OSCILLATORS)
        self.assertNotEqual(oscillators.step(), oscillators)
        self.assertEqual(stepped(oscillators, 2), oscillators)

    def test_still_life_set_is_still(self):
        still = Grid(life.STILL_LIFES)
        self.assertEqual(still.step(), still)

    def test_soup_is_seeded_and_reasonably_dense(self):
        self.assertEqual(life.soup_cells(7), life.soup_cells(7))
        self.assertNotEqual(life.soup_cells(7), life.soup_cells(8))
        population = len(life.soup_cells(7))
        self.assertTrue(5 <= population <= 45)


class CyclerTests(unittest.TestCase):
    def frames(self, cycler, count):
        frames = cycler.frames()
        return [next(frames) for _ in range(count)]

    def test_advances_after_a_still_life(self):
        cycler = life.Cycler(
            patterns=[("Block", life.BLOCK), ("Blinker", life.BLINKER)],
            min_generations=3,
            max_generations=50,
        )
        names = [name for name, _, _ in self.frames(cycler, 5)]
        # The still life is shown for the 3-frame minimum, then yields.
        self.assertEqual(names[:3], ["Block"] * 3)
        self.assertEqual(names[3], "Blinker")

    def test_advances_after_the_board_empties(self):
        cycler = life.Cycler(
            patterns=[("Doomed", [(5, 3)]), ("Block", life.BLOCK)],
            min_generations=1,
            max_generations=50,
        )
        names = [name for name, _, _ in self.frames(cycler, 3)]
        self.assertEqual(names[0], "Doomed")
        self.assertEqual(names[1], "Block")

    def test_generation_cap_advances_a_pattern(self):
        # A glider on the torus would otherwise run for hundreds of
        # generations; the cap must cut it off.
        cycler = life.Cycler(
            patterns=[("Glider", life.GLIDER), ("Block", life.BLOCK)],
            min_generations=2,
            max_generations=5,
        )
        frames = self.frames(cycler, 6)
        generations = [gen for _, _, gen in frames]
        self.assertEqual(generations[:5], [0, 1, 2, 3, 4])
        self.assertEqual(frames[5][0], "Block")

    def test_default_cycle_uses_the_library_and_loops(self):
        cycler = life.Cycler(min_generations=1, max_generations=2)
        self.assertEqual(cycler.pattern_names(), LibraryTests.EXPECTED_NAMES)
        frames = self.frames(cycler, 17)
        # Two frames per pattern (cap of 2), then the library repeats.
        self.assertEqual(frames[0][0], "Glider")
        self.assertEqual(frames[16][0], "Glider")


class CyclerValidationTests(unittest.TestCase):
    """F13: contradictory or nonpositive generation bounds are rejected.

    Before the validation, min_generations=6 with max_generations=2 ran
    a pattern for 6 generations -- the minimum guards every exit check,
    including the cap, so the run silently exceeded the requested max.
    """

    def test_min_above_max_is_rejected(self):
        with self.assertRaises(ValueError):
            life.Cycler(min_generations=6, max_generations=2)

    def test_nonpositive_bounds_are_rejected(self):
        for kwargs in (
            {"min_generations": 0},
            {"min_generations": -1},
            {"max_generations": 0},
            {"max_generations": -3},
            {"min_generations": 0, "max_generations": 0},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    life.Cycler(**kwargs)

    def test_min_equal_max_is_valid_and_obeys_the_cap(self):
        cycler = life.Cycler(
            patterns=[("Block", life.BLOCK), ("Blinker", life.BLINKER)],
            min_generations=2,
            max_generations=2,
        )
        frames_iter = cycler.frames()
        frames = [next(frames_iter) for _ in range(3)]
        generations = [gen for _, _, gen in frames]
        self.assertEqual(generations[:2], [0, 1])
        self.assertEqual(frames[2][0], "Blinker")


class CliValidationTests(unittest.TestCase):
    """The CLI rejects nonfinite/nonpositive fps and bad bounds (F13)."""

    def assert_cli_error(self, argv):
        import q_life

        with self.assertRaises(SystemExit) as caught:
            q_life.main(argv)
        self.assertEqual(caught.exception.code, 2)

    def test_bad_fps_values(self):
        for fps in ("0", "-1", "nan", "inf", "-inf"):
            with self.subTest(fps=fps):
                self.assert_cli_error(["--fps", fps, "--terminal"])

    def test_contradictory_generation_bounds(self):
        self.assert_cli_error(
            ["--max-generations", "2", "--min-generations", "6", "--terminal"]
        )

    def test_nonpositive_generation_bounds(self):
        self.assert_cli_error(["--max-generations", "0", "--terminal"])
        self.assert_cli_error(["--min-generations", "0", "--terminal"])
        self.assert_cli_error(["--min-generations", "-2", "--terminal"])


if __name__ == "__main__":
    unittest.main()
