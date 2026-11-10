#pragma once
#include <array>
#include <cstdint>

namespace sudoku {

constexpr int kSize      = 9;
constexpr int kCells     = kSize * kSize;
constexpr int kMinGivens = 17;   // theoretical minimum for a unique sudoku
constexpr int kMaxGivens = 81;

using Board = std::array<int32_t, kCells>;
// Convention: cells <= 0 are empty, values 1..9 are digits.

/// Solve the puzzle. Throws std::invalid_argument on malformed/duplicate
/// input, std::runtime_error if the puzzle has no solution.
Board solve(const Board& puzzle);

/// True iff the puzzle has exactly one solution.
bool has_unique_solution(const Board& puzzle);

/// Number of solutions, capped at `limit` (>=1).
int count_solutions(const Board& puzzle, int limit);

/// Generate a uniquely-solvable puzzle with exactly `known_numbers` givens.
/// Throws std::invalid_argument if `known_numbers` is outside
/// [kMinGivens, kMaxGivens], std::runtime_error if the generator cannot
/// reach the requested count in time.
Board create_puzzle(uint32_t known_numbers);

/// True iff every cell is filled and no constraint is violated.
bool is_solved(const Board& board);

/// True iff the given (filled) cells do not violate any sudoku constraint.
bool is_consistent(const Board& puzzle);

/// Per-cell difficulty scores in [0, 1]; NaN for cells that were given.
///
/// The score estimates how late a human solver (who only uses naked and
/// hidden singles) would fill each empty cell:
///   * 0.10 — naked single, round 0 (immediately obvious)
///   * 0.15 — hidden single, round 0
///   * 0.10 .. 0.75 — single in a later round (spread across rounds)
///   * 0.80 — hidden single, last round
///   * 0.85 .. 1.00 — requires guessing / advanced techniques
///   * nan  — given cell
std::array<double, kCells> analyze_difficulty(const Board& puzzle);

}  // namespace sudoku
