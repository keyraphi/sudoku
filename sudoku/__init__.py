"""sudoku — fast C++ Sudoku engine with visualization and puzzle analysis.

Quick start::

    from sudoku import generate_pdfs
    generate_pdfs(30, "puzzle.pdf", "solution.pdf")

creates a puzzle PDF and a colour-coded solution PDF in one call.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Union

import numpy as np

from .sudoku_module import (
    solve_sudoku,
    create_sudoku,
    has_unique_solution,
    count_solutions,
    is_solved,
    is_consistent,
    analyze_difficulty,
)
from ._viz import render, render_to_png, render_to_pdf, show

__all__ = [
    "solve_sudoku",
    "create_sudoku",
    "has_unique_solution",
    "count_solutions",
    "is_solved",
    "is_consistent",
    "analyze_difficulty",
    "render",
    "render_to_png",
    "render_to_pdf",
    "show",
    "generate_pdfs",
]


def generate_pdfs(
    known_numbers: int,
    puzzle_path: Union[str, Path],
    solution_path: Union[str, Path],
    *,
    dpi: int = 300,
    paper: str = "a4",
    size: float = 5.0,
    puzzle_title: Optional[str] = "Sudoku",
    solution_title: Optional[str] = "Solution",
    difficulty_legend: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate a puzzle + colour-coded solution as two PDFs in one call.

    Parameters
    ----------
    known_numbers : int
        Number of givens in [17, 81]. Fewer givens → harder puzzle.
        Values below ~22 are hit-or-miss; 25–35 is the sweet spot for
        "human-friendly but non-trivial".
    puzzle_path : str | Path
        Where to save the puzzle PDF (empty cells, givens only).
    solution_path : str | Path
        Where to save the solution PDF. Filled-in digits are coloured
        on a green → yellow → red ramp by how hard they were to deduce.
    dpi : int
        Resolution of the rendered pages.
    paper : {"a4", "letter"}
        Page size for the PDF.
    size : float
        Grid width in inches.
    puzzle_title, solution_title : str, optional
        Captions printed under each grid. Pass ``None`` to omit.
    difficulty_legend : bool
        If True, add an "easy → hard" colour legend to the solution PDF.

    Returns
    -------
    puzzle, solution : tuple[np.ndarray, np.ndarray]
        The generated puzzle and its solution as ``int32`` (9, 9) arrays.
    """
    puzzle   = create_sudoku(known_numbers)
    solution = solve_sudoku(puzzle)
    difficulty = analyze_difficulty(puzzle)

    render_to_pdf(
        puzzle, puzzle_path,
        size=size, dpi=dpi, paper=paper,
        title=puzzle_title,
    )
    render_to_pdf(
        puzzle, solution_path,
        solution=solution,
        difficulty=difficulty,
        difficulty_legend=difficulty_legend,
        size=size, dpi=dpi, paper=paper,
        title=solution_title,
    )
    return puzzle, solution
