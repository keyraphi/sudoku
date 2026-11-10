#include <cmath>
#include <cstdint>
#include <cstring>
#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/string.h>

#include "sudoku_backend.hpp"

namespace nb = nanobind;
using namespace nb::literals;

// A (9, 9) C-contiguous int32 array. Accepts numpy/pytorch/etc. on input,
// returns numpy on output.
using Sudoku_t = nb::ndarray<nb::numpy, int32_t, nb::shape<9, 9>,
                             nb::c_contig, nb::device::cpu>;

// A (9, 9) float64 array for difficulty scores (NaN = given cell).
using Difficulty_t = nb::ndarray<nb::numpy, double, nb::shape<9, 9>,
                                 nb::c_contig, nb::device::cpu>;

namespace {

sudoku::Board to_board(const Sudoku_t& arr) {
  const auto* p = static_cast<const int32_t*>(arr.data());
  sudoku::Board b{};
  for (int i = 0; i < sudoku::kCells; ++i) b[i] = p[i];
  return b;
}

Sudoku_t from_board(const sudoku::Board& b) {
  auto* out = new int32_t[sudoku::kCells];
  std::memcpy(out, b.data(), sizeof(int32_t) * sudoku::kCells);
  nb::capsule owner(out, [](void* p) noexcept {
    delete[] static_cast<int32_t*>(p);
  });
  return Sudoku_t(out, {9, 9}, owner);
}

Difficulty_t from_difficulty(const std::array<double, sudoku::kCells>& s) {
  auto* out = new double[sudoku::kCells];
  std::memcpy(out, s.data(), sizeof(double) * sudoku::kCells);
  nb::capsule owner(out, [](void* p) noexcept {
    delete[] static_cast<double*>(p);
  });
  return Difficulty_t(out, {9, 9}, owner);
}

}  // namespace

Sudoku_t solve_sudoku(const Sudoku_t& sudoku) {
  return from_board(sudoku::solve(to_board(sudoku)));
}

Sudoku_t create_sudoku(uint32_t known_numbers) {
  return from_board(sudoku::create_puzzle(known_numbers));
}

bool py_has_unique_solution(const Sudoku_t& sudoku) {
  return sudoku::has_unique_solution(to_board(sudoku));
}

int py_count_solutions(const Sudoku_t& sudoku, int limit) {
  return sudoku::count_solutions(to_board(sudoku), limit);
}

bool py_is_solved(const Sudoku_t& sudoku) {
  return sudoku::is_solved(to_board(sudoku));
}

bool py_is_consistent(const Sudoku_t& sudoku) {
  return sudoku::is_consistent(to_board(sudoku));
}

Difficulty_t py_analyze_difficulty(const Sudoku_t& sudoku) {
  return from_difficulty(sudoku::analyze_difficulty(to_board(sudoku)));
}

NB_MODULE(sudoku_module, m) {
  m.def("solve_sudoku", &solve_sudoku, "sudoku"_a,
        R"doc(Solves the given Sudoku.

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
)doc");

  m.def("create_sudoku", &create_sudoku, "known_numbers"_a,
        R"doc(Create a uniquely solvable sudoku.

Parameters
----------
known_numbers : int
    Number of givens. Must be in [17, 81]. Values below ~22 rarely succeed.

Returns
-------
ndarray[int32, (9, 9)]
    A sudoku puzzle. Values <= 0 are empty.
)doc");

  m.def("has_unique_solution", &py_has_unique_solution, "sudoku"_a,
        "True iff the puzzle has exactly one solution.");

  m.def("count_solutions", &py_count_solutions, "sudoku"_a, "limit"_a = 2,
        "Counts solutions of the puzzle, capped at `limit`.");

  m.def("is_solved", &py_is_solved, "sudoku"_a,
        "True iff the grid is fully filled and consistent.");

  m.def("is_consistent", &py_is_consistent, "sudoku"_a,
        "True iff the given digits do not violate any constraint.");

  m.def("analyze_difficulty", &py_analyze_difficulty, "sudoku"_a,
        R"doc(Per-cell difficulty scores in [0, 1].

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
)doc");
}
