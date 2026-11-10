"""Real tests for fast-sudoku: known puzzle, generation properties, analysis."""
import numpy as np
import pytest
from sudoku import (
    solve_sudoku,
    create_sudoku,
    has_unique_solution,
    count_solutions,
    is_solved,
    is_consistent,
    analyze_difficulty,
)


# ---------------------------------------------------------------------------
# Fixtures: a known puzzle and its unique solution
# ---------------------------------------------------------------------------
@pytest.fixture
def known_puzzle() -> np.ndarray:
    """A classic easy Sudoku with a unique solution."""
    return np.array([
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9],
    ], dtype=np.int32)


@pytest.fixture
def known_solution() -> np.ndarray:
    return np.array([
        [5, 3, 4, 6, 7, 8, 9, 1, 2],
        [6, 7, 2, 1, 9, 5, 3, 4, 8],
        [1, 9, 8, 3, 4, 2, 5, 6, 7],
        [8, 5, 9, 7, 6, 1, 4, 2, 3],
        [4, 2, 6, 8, 5, 3, 7, 9, 1],
        [7, 1, 3, 9, 2, 4, 8, 5, 6],
        [9, 6, 1, 5, 3, 7, 2, 8, 4],
        [2, 8, 7, 4, 1, 9, 6, 3, 5],
        [3, 4, 5, 2, 8, 6, 1, 7, 9],
    ], dtype=np.int32)


# ---------------------------------------------------------------------------
# Core solver
# ---------------------------------------------------------------------------
def test_solve_known_puzzle(known_puzzle, known_solution):
    solved = solve_sudoku(known_puzzle)
    np.testing.assert_array_equal(solved, known_solution)


def test_is_solved(known_solution):
    assert is_solved(known_solution)


def test_is_not_solved(known_puzzle):
    assert not is_solved(known_puzzle)


def test_is_consistent(known_puzzle):
    assert is_consistent(known_puzzle)


def test_solve_unsolvable_raises():
    bad = np.zeros((9, 9), dtype=np.int32)
    bad[0, 0] = bad[0, 1] = 5  # duplicate in row 0
    with pytest.raises(ValueError, match="duplicate"):
        solve_sudoku(bad)


def test_out_of_range_raises():
    bad = np.zeros((9, 9), dtype=np.int32)
    bad[0, 0] = 10
    with pytest.raises(ValueError, match="values must be"):
        solve_sudoku(bad)


# ---------------------------------------------------------------------------
# Uniqueness and counting
# ---------------------------------------------------------------------------
def test_has_unique_solution(known_puzzle):
    assert has_unique_solution(known_puzzle)


def test_count_solutions(known_puzzle):
    assert count_solutions(known_puzzle, limit=2) == 1


def test_empty_board_has_many_solutions():
    empty = np.zeros((9, 9), dtype=np.int32)
    assert count_solutions(empty, limit=2) == 2  # capped at 2


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("givens", [25, 30, 35])
def test_create_sudoku(givens):
    puzzle = create_sudoku(givens)
    assert puzzle.shape == (9, 9)
    assert puzzle.dtype == np.int32
    assert (puzzle > 0).sum() == givens
    assert is_consistent(puzzle)
    assert has_unique_solution(puzzle)


def test_create_sudoku_invalid_range():
    with pytest.raises(ValueError):
        create_sudoku(16)   # below minimum
    with pytest.raises(ValueError):
        create_sudoku(82)   # above maximum


# ---------------------------------------------------------------------------
# Difficulty analysis
# ---------------------------------------------------------------------------
def test_analyze_difficulty_shape(known_puzzle):
    scores = analyze_difficulty(known_puzzle)
    assert scores.shape == (9, 9)
    assert scores.dtype == np.float64


def test_analyze_difficulty_givens_are_nan(known_puzzle):
    scores = analyze_difficulty(known_puzzle)
    givens_mask = known_puzzle > 0
    assert np.isnan(scores[givens_mask]).all()


def test_analyze_difficulty_empties_are_finite(known_puzzle):
    scores = analyze_difficulty(known_puzzle)
    empties_mask = known_puzzle == 0
    assert np.isfinite(scores[empties_mask]).all()


def test_analyze_difficulty_range(known_puzzle):
    scores = analyze_difficulty(known_puzzle)
    valid = scores[np.isfinite(scores)]
    assert (valid >= 0.0).all()
    assert (valid <= 1.0).all()


def test_analyze_difficulty_rejects_inconsistent():
    bad = np.zeros((9, 9), dtype=np.int32)
    bad[0, 0] = bad[0, 1] = 5
    with pytest.raises(ValueError, match="duplicate"):
        analyze_difficulty(bad)


# ---------------------------------------------------------------------------
# Round-trip on generated puzzles
# ---------------------------------------------------------------------------
def test_generated_puzzle_roundtrip():
    puzzle = create_sudoku(30)
    solution = solve_sudoku(puzzle)
    assert is_solved(solution)
    # Every given must match the solution
    mask = puzzle > 0
    np.testing.assert_array_equal(puzzle[mask], solution[mask])
