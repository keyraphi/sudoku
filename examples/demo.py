#!/usr/bin/env python3
"""End-to-end demonstration of every feature in the `fast-sudoku` library.

Run with::

    python examples/demo.py

All output is written to ``examples/output/``.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

from sudoku import (
    create_sudoku,
    solve_sudoku,
    has_unique_solution,
    count_solutions,
    is_solved,
    is_consistent,
    analyze_difficulty,
    render,
    render_to_png,
    render_to_pdf,
    generate_pdfs,
)

HERE = Path(__file__).resolve().parent
OUT  = HERE / "output"
OUT.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def header(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def sub(title: str) -> None:
    print(f"\n-- {title} --")


def timed(label: str, fn, *args, **kwargs):
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"    {label:<32} {dt:8.3f} ms")
    return result


def print_board(board, title: str | None = None) -> None:
    if title:
        print(f"  {title}")
    for r in range(9):
        if r > 0 and r % 3 == 0:
            print("  ------+-------+------")
        line = ""
        for c in range(9):
            if c > 0 and c % 3 == 0:
                line += " | "
            v = int(board[r, c])
            line += " ." if v == 0 else f" {v}"
        print("  " + line)


def print_difficulty(scores: np.ndarray, puzzle: np.ndarray) -> None:
    """Print a difficulty grid; given cells show as '  .  '."""
    print("  difficulty per cell  ('.' = given, number = score 0.0–1.0)")
    print("  " + "-" * (9 * 6 - 1))
    for r in range(9):
        if r > 0 and r % 3 == 0:
            print("  " + "-" * (9 * 6 - 1))
        row = []
        for c in range(9):
            if puzzle[r, c] != 0:
                row.append("   .  ")
            else:
                row.append(f"{scores[r, c]:5.2f} ")
        print("  " + " ".join(row))


def save(img, name: str) -> Path:
    path = OUT / name
    img.save(path)
    print(f"    saved -> {path}")
    return path


# ---------------------------------------------------------------------------
# 1. Core engine
# ---------------------------------------------------------------------------
def demo_core() -> np.ndarray:
    header("1. Core engine")

    sub("Generate a uniquely-solvable puzzle with 30 givens")
    puzzle = timed("create_sudoku(30)", create_sudoku, 30)
    print_board(puzzle, "generated puzzle")

    sub("Inspect the puzzle")
    t0 = time.perf_counter()
    unique = has_unique_solution(puzzle)
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"    has_unique_solution            {'yes' if unique else 'no'}"
          f"   ({dt:.3f} ms)")
    print(f"    is_consistent                  {is_consistent(puzzle)}")
    print(f"    is_solved                      {is_solved(puzzle)}")
    n = count_solutions(puzzle, 2)
    print(f"    count_solutions(limit=2)       {n}")

    sub("Solve the puzzle")
    solution = timed("solve_sudoku()", solve_sudoku, puzzle)
    print_board(solution, "solution")
    assert is_solved(solution), "solver produced an invalid board"

    sub("Try to solve an inconsistent board (should raise)")
    bad = np.zeros((9, 9), dtype=np.int32)
    try:
        bad[0, 0] = bad[0, 1] = 5
        solve_sudoku(bad)
    except Exception as e:
        print(f"    raised {type(e).__name__}: {e}")

    return puzzle


# ---------------------------------------------------------------------------
# 2. Difficulty analysis
# ---------------------------------------------------------------------------
def demo_analysis(puzzle: np.ndarray) -> None:
    header("2. Difficulty analysis")

    sub("Per-cell scores (0 = obvious, 1 = requires guessing)")
    scores = timed("analyze_difficulty()", analyze_difficulty, puzzle)
    print_difficulty(scores, puzzle)

    empties = puzzle == 0
    valid = scores[empties]
    print()
    print(f"    givens                         {int((puzzle > 0).sum())}")
    print(f"    empty cells                    {int(empties.sum())}")
    print(f"    min / max difficulty           {valid.min():.2f} / {valid.max():.2f}")
    print(f"    mean difficulty                {valid.mean():.2f}")
    print(f"    fraction requiring guessing    "
          f"{(valid >= 0.85).sum()}/{len(valid)}")

    sub("Difficulty distribution (rough histogram)")
    bins = [(0.0, 0.20), (0.20, 0.40), (0.40, 0.60),
            (0.60, 0.80), (0.80, 1.01)]
    labels = ["naked single, round 0",
              "early deduction",
              "mid deduction",
              "late deduction",
              "requires guessing"]
    for (lo, hi), label in zip(bins, labels):
        count = int(((valid >= lo) & (valid < hi)).sum())
        bar = "█" * count
        print(f"    {lo:.1f}–{hi:.1f}  {label:<22} {count:>2}  {bar}")

    sub("Comparison across given counts")
    print(f"    {'givens':>6}  {'empties':>7}  {'mean':>6}  {'guess%':>7}")
    for givens in (25, 30, 35, 40):
        try:
            p = create_sudoku(givens)
            s = analyze_difficulty(p)
            e = s[p == 0]
            guess_frac = (e >= 0.85).mean() * 100
            print(f"    {givens:>6}  {len(e):>7}  {e.mean():>6.2f}  "
                  f"{guess_frac:>6.1f}%")
        except RuntimeError as exc:
            print(f"    {givens:>6}  generation failed: {exc}")


# ---------------------------------------------------------------------------
# 3. Rendering
# ---------------------------------------------------------------------------
def demo_visualization(puzzle: np.ndarray, solution: np.ndarray,
                       difficulty: np.ndarray) -> None:
    header("3. Rendering")

    sub("Plain puzzle PNG (for reading)")
    render_to_png(puzzle, OUT / "puzzle_blank.png",
                  size=6, dpi=300, title="Daily Sudoku")
    print(f"    saved -> {OUT / 'puzzle_blank.png'}")

    sub("Puzzle + solution PNG (solution digits in blue)")
    render_to_png(puzzle, OUT / "puzzle_with_solution.png",
                  solution=solution, size=5, dpi=150,
                  title="Sudoku — solved")
    print(f"    saved -> {OUT / 'puzzle_with_solution.png'}")

    sub("Puzzle + solution PNG (solution digits coloured by difficulty)")
    render_to_png(puzzle, OUT / "puzzle_with_difficulty.png",
                  solution=solution, difficulty=difficulty,
                  difficulty_legend=True,
                  size=5, dpi=150, title="Difficulty")
    print(f"    saved -> {OUT / 'puzzle_with_difficulty.png'}")

    sub("Print-ready PDF (centred on A4, solution + difficulty legend)")
    render_to_pdf(puzzle, OUT / "puzzle_a4.pdf",
                  solution=solution, difficulty=difficulty,
                  difficulty_legend=True,
                  size=5, dpi=300, paper="a4",
                  title="Solution")
    print(f"    saved -> {OUT / 'puzzle_a4.pdf'}")

    sub("Glow overlay (green = solvable, red = contradiction)")
    img = render(puzzle, solution=solution, size=4, dpi=150,
                 glow_color="#22aa44", title="Solved ✓")
    save(img, "puzzle_green_glow.png")

    img = render(puzzle, solution=solution, size=4, dpi=150,
                 glow_color="#cc2222", title="Contradiction ✗")
    save(img, "puzzle_red_glow.png")


# ---------------------------------------------------------------------------
# 4. One-liner: puzzle + solution as two PDFs
# ---------------------------------------------------------------------------
def demo_generate_pdfs() -> None:
    header("4. One-liner — puzzle + solution PDFs")

    sub("generate_pdfs(30, 'puzzle.pdf', 'solution.pdf')")
    puzzle_path   = OUT / "onepager_puzzle.pdf"
    solution_path = OUT / "onepager_solution.pdf"
    t0 = time.perf_counter()
    puzzle, solution = generate_pdfs(
        known_numbers=30,
        puzzle_path=puzzle_path,
        solution_path=solution_path,
        puzzle_title="Sudoku",
        solution_title="Solution",
    )
    dt = (time.perf_counter() - t0) * 1000.0
    print(f"    total time                     {dt:8.1f} ms")
    print(f"    saved -> {puzzle_path}")
    print(f"    saved -> {solution_path}")
    print(f"    puzzle has {int((puzzle > 0).sum())} givens, "
          f"{int((puzzle == 0).sum())} empty cells")

    sub("Batch: five puzzles at different difficulties")
    for i, givens in enumerate((25, 28, 32, 36, 40), start=1):
        p_path = OUT / f"batch_{i:02d}_puzzle.pdf"
        s_path = OUT / f"batch_{i:02d}_solution.pdf"
        try:
            generate_pdfs(givens, p_path, s_path,
                          puzzle_title=f"Puzzle {i}  ({givens} givens)",
                          solution_title=f"Solution {i}")
            print(f"    [{givens:>2} givens] {p_path.name}  +  {s_path.name}")
        except RuntimeError as exc:
            print(f"    [{givens:>2} givens] generation failed: {exc}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> int:
    print(f"using sudoku module from: {__import__('sudoku').__file__}")
    print(f"output directory: {OUT}")

    puzzle     = demo_core()
    solution   = solve_sudoku(puzzle)
    difficulty = analyze_difficulty(puzzle)

    demo_analysis(puzzle)
    demo_visualization(puzzle, solution, difficulty)
    demo_generate_pdfs()

    header("Done")
    print(f"  All files written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
