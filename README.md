# Game of Life on the Arduino Uno Q

Conway's Game of Life, played on the Arduino Uno Q's built-in 8x13 LED
matrix. It cycles through a library of classic patterns forever -- the
kind of thing you leave running on a shelf. The board wraps around at
every edge (a torus), which on a board this small is what keeps the
patterns in play instead of dying against a wall.

**The rules** (B3/S23): every cell is re-evaluated each generation from
its eight neighbors -- a live cell with 2 or 3 live neighbors survives, a
dead cell with exactly 3 live neighbors is born, and every other cell
dies or stays dead. That is the whole game; everything else is
consequences.

## The show

Each pattern runs until the board empties, a state repeats (a still life
or a settled cycle), or 150 generations pass -- but always for at least
6 generations, so even the motionless patterns get their moment. Then
the next pattern takes the stage, and after the last one the show loops.

- **Glider** -- the five-cell walker
- **Lightweight spaceship** -- the smallest true spaceship
- **R-pentomino** -- five cells, a long chaotic youth
- **Diehard** -- named for how long it takes to vanish completely
- **Acorn** -- grows far beyond its seven cells
- **Oscillators** -- blinker, toad, and beacon, keeping time together
- **Still lifes** -- block, beehive, loaf, boat, and tub, sitting still
- **Random soup** -- a seeded random board (about 20% density)

## Running it on the Uno Q

You need:

- The **matrix-bridge sketch** flashed on the Q's MCU -- it is in
  `hardware/unoq-matrix-bridge/` in this repo, with build/flash notes in
  the sketch itself. (If the Q already runs a duel rig with an LED
  matrix display, the sketch is already there.)
- The **`arduino-router-bridge`** Python package on the Linux side
  (preinstalled on the Q's image).

Then:

```
python3 q_life.py                 # 5 generations per second
python3 q_life.py --fps 10        # faster
python3 q_life.py --seed 42       # a different random-soup round
```

Ctrl-C stops it and blanks the matrix.

## Running it anywhere else

No matrix? The show falls back to the terminal -- one text frame per
generation -- which works on any machine with Python 3:

```
python3 q_life.py --terminal      # force terminal mode
```

(The fallback also kicks in automatically if the matrix can't be
reached, or is lost mid-run.)

## Sharing the matrix

This drives the same LED matrix that other programs (such as a duel
rig's `--display` option) use. There is one matrix and no sharing
protocol: run this when nothing else is driving the display, and stop
it (Ctrl-C) before starting something that does.

## Layout

- `life.py` -- the engine: toroidal 13x8 grid, B3/S23, the pattern
  library, and the pattern cycler. Pure Python, no hardware imports.
- `q_life.py` -- the runner: computes generations and pushes frames to
  the matrix, or to the terminal when there is no matrix.
- `unoq_matrix.py` -- the matrix driver, borrowed from the `dual`
  project (same author). One change from the original: the column mask
  is `0xFF` instead of `0x7F`, because this board needs all 8 rows --
  the original's 5x7 text font never lights the bottom row, so the mask
  made no difference there. The change is commented in the file.
- `hardware/unoq-matrix-bridge/` -- the MCU sketch exposing the `draw`
  RPC the driver talks to, copied from the same place.
- `tests/` -- the rules, proven: `python3 -m unittest discover -s tests`

No third-party dependencies: the engine and runner are standard library
only; the only package involved is `arduino-router-bridge`, and only on
the Q, only for the matrix transport.
