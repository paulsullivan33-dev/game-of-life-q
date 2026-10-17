#!/usr/bin/env python3
"""q_life.py -- Conway's Game of Life on the Arduino Uno Q's LED matrix.

Plays life.py's pattern library on the matrix forever: each pattern runs
until it dies out, settles into a cycle, or reaches the generation cap,
then the next one takes the stage. It is meant for the idle hours --
run it when nothing else is using the matrix, and stop it with Ctrl-C.

Display: the Uno Q matrix, through unoq_matrix.py (the Router Bridge
transport needs the matrix-bridge sketch flashed on the MCU; see
hardware/). If the matrix cannot be reached -- wrong machine, sketch
not flashed, bridge down -- the show falls back to the terminal, one
text frame per generation, so the program runs anywhere.

Examples:
    python3 q_life.py                  # matrix, 5 generations/second
    python3 q_life.py --fps 10         # faster
    python3 q_life.py --terminal       # force terminal mode
"""

import argparse
import sys
import time

import life

ON_BYTE = 0xFF  # a fully lit column byte; the driver scales brightness


def grid_columns(grid):
    """Pack a Grid into the driver's 13 column bytes (LSB = top pixel)."""
    columns = [0] * life.COLS
    for x, y in grid.cells:
        columns[x] |= 1 << y
    return columns


def open_matrix():
    """Return a matrix driver, or None if the matrix is unreachable."""
    try:
        from unoq_matrix import create_matrix

        return create_matrix()
    except Exception as exc:  # import failure or DisplayUnavailable
        print(f"No LED matrix ({exc}); falling back to the terminal.")
        return None


def show_terminal(name, grid, generation):
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")
    print(f"{name} -- generation {generation}")
    print(grid)
    print(flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Conway's Game of Life on the Uno Q LED matrix."
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=5.0,
        help="generations per second (default: 5)",
    )
    parser.add_argument(
        "--max-generations",
        type=int,
        default=life.DEFAULT_MAX_GENERATIONS,
        help="generations before a pattern yields the stage "
        f"(default: {life.DEFAULT_MAX_GENERATIONS})",
    )
    parser.add_argument(
        "--min-generations",
        type=int,
        default=life.DEFAULT_MIN_GENERATIONS,
        help="generations a pattern is shown at minimum "
        f"(default: {life.DEFAULT_MIN_GENERATIONS})",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="seed for the random-soup round (default: 0)",
    )
    parser.add_argument(
        "--terminal",
        action="store_true",
        help="render in the terminal instead of on the LED matrix",
    )
    args = parser.parse_args(argv)
    if args.fps <= 0:
        parser.error("--fps must be positive")

    matrix = None if args.terminal else open_matrix()
    cycler = life.Cycler(
        max_generations=args.max_generations,
        min_generations=args.min_generations,
        seed=args.seed,
    )
    delay = 1.0 / args.fps
    try:
        for name, grid, generation in cycler.frames():
            if matrix is not None:
                try:
                    matrix._write(grid_columns(grid))  # pylint: disable=W0212
                except Exception as exc:
                    print(f"Matrix lost ({exc}); falling back to the terminal.")
                    matrix = None
                    show_terminal(name, grid, generation)
            else:
                show_terminal(name, grid, generation)
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if matrix is not None:
            try:
                matrix.clear()
            except Exception:
                pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
