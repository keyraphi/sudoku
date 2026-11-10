from typing import Annotated

import numpy
from numpy.typing import NDArray


def solve_sudoku(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]) -> Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]:
    """
    Solves the given Sudoku.

    Parameters
    ----------
    sudoku : ndarray[int32, (9, 9)]
        A 9x9 int32 array. Values <= 0 are empty, 1..9 are digits.

    Returns
    -------
    ndarray[int32, (9, 9)]
        The solved sudoku.

    Raises
    ------
    ValueError
        If `sudoku` contains duplicate digits or values > 9.
    RuntimeError
        If `sudoku` has no solution.
    """

def create_sudoku(known_numbers: int) -> Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]:
    """
    Create a uniquely solvable sudoku.

    Parameters
    ----------
    known_numbers : int
        Number of givens. Must be in [17, 81]. Values below ~22 rarely succeed.

    Returns
    -------
    ndarray[int32, (9, 9)]
        A sudoku puzzle. Values <= 0 are empty.
    """

def has_unique_solution(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]) -> bool:
    """True iff the puzzle has exactly one solution."""

def count_solutions(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')], limit: int = 2) -> int:
    """Counts solutions of the puzzle, capped at `limit`."""

def is_solved(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]) -> bool:
    """True iff the grid is fully filled and consistent."""

def is_consistent(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]) -> bool:
    """True iff the given digits do not violate any constraint."""

def analyze_difficulty(sudoku: Annotated[NDArray[numpy.int32], dict(shape=(9, 9), order='C', device='cpu')]) -> Annotated[NDArray[numpy.float64], dict(shape=(9, 9), order='C', device='cpu')]:
    """
    Per-cell difficulty scores in [0, 1].

    Estimates how late a human solver would fill each empty cell, based on
    rounds of single-step deductions (naked + hidden singles):

      * ``0.10`` — naked single, round 0 (immediately obvious)
      * ``0.15`` — hidden single, round 0
      * ``0.10 .. 0.75`` — single in a later round (spread across rounds)
      * ``0.80`` — hidden single, last round
      * ``0.85 .. 1.00`` — requires guessing / advanced techniques
      * ``nan`` — given cell

    Parameters
    ----------
    sudoku : ndarray[int32, (9, 9)]
        A 9x9 int32 array. Values <= 0 are empty, 1..9 are digits.

    Returns
    -------
    ndarray[float64, (9, 9)]
        Difficulty score per cell. ``nan`` for givens.

    Raises
    ------
    ValueError
        If ``sudoku`` contains duplicate digits or values > 9.
    """
