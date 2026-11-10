# fast-sudoku

A fast C++ Sudoku engine with a NumPy-based Python bridge, print-ready PDF
rendering, and per-cell difficulty analysis.

- **Generate** uniquely-solvable puzzles with a chosen number of givens.
- **Solve** any 9×9 Sudoku in microseconds (MRV + bitmask backtracking).
- **Analyze** every empty cell: how late would a human solver reach it?
- **Render** to PNG or print-ready PDF; colour solution digits on an
  easy → hard ramp.
- **One-liner** to produce puzzle + solution PDFs.

Built with [nanobind](https://github.com/wjakob/nanobind) and
[scikit-build-core](https://scikit-build-core.readthedocs.io/).

---

## Installation

```bash
pip install fast-sudoku
```

Prebuilt wheels are published for CPython 3.10–3.14 on Linux (manylinux
2.28, x86_64). On other platforms `pip` builds from source; you will need
a C++20 compiler and CMake ≥ 3.25.

### From source (development)

```bash
git clone https://github.com/keyraphi/sudoku.git
cd sudoku
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

OpenMP is strongly recommended (generation is ~10× faster). It is detected
automatically; if your compiler does not ship it, the build falls back to
serial generation.

> **Manjaro / Arch note:** `pip` refuses to install into the system Python
> (`externally-managed-environment`). Always work inside a virtual
> environment, as shown above.

---

## Quick start

```python
import numpy as np
from sudoku import (
    create_sudoku, solve_sudoku,
    is_solved, analyze_difficulty,
)

# 1. Generate a puzzle with 30 givens
puzzle = create_sudoku(30)

# 2. Solve it
solution = solve_sudoku(puzzle)
assert is_solved(solution)

# 3. Per-cell difficulty scores in [0, 1]; nan for givens
scores = analyze_difficulty(puzzle)
print(scores)
```

### One-liner: puzzle + solution as PDFs

```python
from sudoku import generate_pdfs

puzzle, solution = generate_pdfs(
    known_numbers=30,
    puzzle_path="puzzle.pdf",
    solution_path="solution.pdf",
)
```

`puzzle.pdf` is a clean puzzle, ready to print. `solution.pdf` is the same
grid with the solution filled in, every digit coloured by difficulty:

- **green** — round-0 naked or hidden single (immediately obvious)
- **yellow** — single after a few rounds of deduction
- **red** — single in the last round, or requires guessing

The solution page includes an “easy → hard” legend by default.

---

## API

All board functions take and return C-contiguous `(9, 9)` `int32` NumPy
arrays. Cells with value `≤ 0` are empty; `1`–`9` are digits.

### Core engine (C++)

| Function | Purpose |
| --- | --- |
| `solve_sudoku(board)` | Solve the puzzle. Raises `RuntimeError` if unsolvable. |
| `create_sudoku(n)` | Generate a uniquely-solvable puzzle with `n` givens (`17 ≤ n ≤ 81`). |
| `has_unique_solution(board)` | `True` iff exactly one solution exists. |
| `count_solutions(board, limit=2)` | Count solutions, capped at `limit`. |
| `is_solved(board)` | Fully filled and consistent? |
| `is_consistent(board)` | No duplicate digits? |

### Analysis

| Function | Purpose |
| --- | --- |
| `analyze_difficulty(board)` | `float64 (9, 9)` scores in `[0, 1]`; `nan` for givens. |

### Rendering

| Function | Purpose |
| --- | --- |
| `render(board, **opts)` | Render to a `PIL.Image`. |
| `render_to_png(board, path, **opts)` | Save as PNG. |
| `render_to_pdf(board, path, **opts)` | Save as PDF, centred on A4 or Letter. |
| `show(board_or_image, **opts)` | Open in the system viewer or inline in notebooks. |
| `generate_pdfs(n, puzzle_pdf, solution_pdf, **opts)` | One-call puzzle + colour-coded solution. |

`render` / `render_to_pdf` accept:

| Option | Default | Meaning |
| --- | --- | --- |
| `solution` | `None` | Digits to fill into empty cells |
| `difficulty` | `None` | `(9, 9)` scores colouring the solution digits |
| `difficulty_legend` | `False` | Add an easy → hard bar below the grid |
| `size` | `6.0` | Grid width in inches |
| `dpi` | `150` (PNG) / `300` (PDF) | Output resolution |
| `title` | `None` | Caption below the grid |
| `glow_color` | `None` | Optional coloured halo around the grid |

---

## How difficulty is scored

The analyzer simulates a human solver who only uses **naked singles** and
**hidden singles**, filling the board in rounds:

1. **Round 0** fills every cell that is already a naked single (one
   candidate) or a hidden single (only cell in its row / column / box that
   can hold a digit).
2. **Round 1** repeats on the updated board, and so on.
3. Cells that are never forced — because the puzzle requires guessing or
   advanced techniques — get the highest scores.

The final score blends three pieces of information:

| Situation | Score |
| --- | --- |
| Naked single, round 0 | `0.10` |
| Hidden single, round 0 | `0.15` |
| Single in the last round | `0.75` – `0.84` |
| Requires guessing, 2 candidates | `0.85` |
| Requires guessing, 9 candidates | `1.00` |
| Given | `nan` |

Because the score is round-normalised, a puzzle where every empty cell falls
in round 0 gets greens everywhere, while a puzzle that requires guessing
concentrates reds in the cells that survive to the end. This is the
information you need to see *where* a puzzle is hard, not just *whether* it is.

---

## Rendering example

```python
from sudoku import create_sudoku, solve_sudoku, analyze_difficulty, render

puzzle     = create_sudoku(30)
solution   = solve_sudoku(puzzle)
difficulty = analyze_difficulty(puzzle)

render(
    puzzle,
    solution=solution,
    difficulty=difficulty,
    difficulty_legend=True,
    size=6, dpi=150,
    title="Daily Sudoku",
).show()
```

Or write the pair of PDFs in a single call:

```python
from sudoku import generate_pdfs
generate_pdfs(28, "puzzle.pdf", "solution.pdf")
```

---

## Building from scratch

```bash
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

The Python extension is written to `build/src/sudoku_module.*.so`, the type
stub to `sudoku/sudoku_module.pyi`.

Requirements:

| Component | Minimum | Notes |
| --- | --- | --- |
| CMake | 3.25 | |
| C++ compiler | C++20 | GCC 13+, Clang 16+ |
| Python | 3.10 | Development headers required |
| OpenMP | optional | Strongly recommended |

---

## Development

```bash
source .venv/bin/activate
pip install -e .[dev]

pytest                     # test suite
basedpyright               # type checking
ruff check . && ruff format .
```

The C++ backend is in `src/sudoku_backend.cpp` (solver, generator, analyzer);
the nanobind bridge is `src/sudoku.cpp`; the Python package is under
`sudoku/`.

### Publishing a release

Wheels for CPython 3.10–3.14 (manylinux 2.28, x86_64) are built inside a
Docker container:

```bash
docker run --rm -v "$(pwd)":/io cuda13_builder /io/build_wheels.sh
```

The repaired wheels land in `wheelhouse/`. Upload with `twine`:

```bash
twine check wheelhouse/*
twine upload --repository pypi wheelhouse/*
```

---

## License

MIT — see [LICENSE](LICENSE).
