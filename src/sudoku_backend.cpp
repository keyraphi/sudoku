#include "sudoku_backend.hpp"

#include <algorithm>
#include <atomic>
#include <bit>
#include <chrono>
#include <cstring>
#include <limits>
#include <numeric>
#include <optional>
#include <random>
#include <stdexcept>

#ifdef _OPENMP
#include <omp.h>
#endif

namespace sudoku {
namespace {

constexpr uint16_t kAllDigits = 0x3FE; // bits 1..9 set

inline int box_of(int idx) noexcept {
  const int r = idx / 9, c = idx % 9;
  return (r / 3) * 3 + (c / 3);
}

// ---------------------------------------------------------------------------
// Fast MRV backtracking solver.
// ---------------------------------------------------------------------------
struct FastSolver {
  std::array<int32_t, kCells> cells{};
  std::array<uint16_t, 9> row_m{};
  std::array<uint16_t, 9> col_m{};
  std::array<uint16_t, 9> box_m{};
  std::array<int32_t, kCells> solution{};

  int solutions = 0;
  int limit = 1;
  bool randomize = false;
  std::mt19937 *rng = nullptr;

  bool load(const Board &b) {
    row_m.fill(0);
    col_m.fill(0);
    box_m.fill(0);
    for (int i = 0; i < kCells; ++i) {
      const int32_t v = b[i];
      if (v < 0 || v > 9)
        return false;
      cells[i] = v;
      if (v != 0) {
        const uint16_t bit = static_cast<uint16_t>(1u << v);
        const int r = i / 9, c = i % 9, bx = box_of(i);
        if ((row_m[r] | col_m[c] | box_m[bx]) & bit)
          return false;
        row_m[r] |= bit;
        col_m[c] |= bit;
        box_m[bx] |= bit;
      }
    }
    return true;
  }

  uint16_t candidates(int idx) const noexcept {
    const int r = idx / 9, c = idx % 9, bx = box_of(idx);
    return static_cast<uint16_t>(~(row_m[r] | col_m[c] | box_m[bx]) &
                                 kAllDigits);
  }

  void search() {
    if (solutions >= limit)
      return;

    int best_idx = -1, best_n = 10;
    uint16_t best_cands = 0;
    for (int i = 0; i < kCells; ++i) {
      if (cells[i] != 0)
        continue;
      const uint16_t cand = candidates(i);
      const int n = std::popcount(cand);
      if (n < best_n) {
        best_n = n;
        best_idx = i;
        best_cands = cand;
        if (n == 0)
          break;
      }
    }

    if (best_idx == -1) {
      if (solutions == 0)
        solution = cells;
      ++solutions;
      return;
    }
    if (best_n == 0)
      return;

    const int r = best_idx / 9;
    const int c = best_idx % 9;
    const int bx = box_of(best_idx);

    if (randomize && rng != nullptr) {
      int digits[9];
      int n = 0;
      uint16_t cand = best_cands;
      while (cand != 0) {
        digits[n++] = std::countr_zero(cand);
        cand = static_cast<uint16_t>(cand & (cand - 1));
      }
      std::shuffle(digits, digits + n, *rng);
      for (int k = 0; k < n; ++k) {
        const int d = digits[k];
        const uint16_t bit = static_cast<uint16_t>(1u << d);
        cells[best_idx] = d;
        row_m[r] |= bit;
        col_m[c] |= bit;
        box_m[bx] |= bit;
        search();
        cells[best_idx] = 0;
        row_m[r] &= ~bit;
        col_m[c] &= ~bit;
        box_m[bx] &= ~bit;
        if (solutions >= limit)
          return;
      }
    } else {
      uint16_t cand = best_cands;
      while (cand != 0) {
        const int d = std::countr_zero(cand);
        cand = static_cast<uint16_t>(cand & (cand - 1));
        const uint16_t bit = static_cast<uint16_t>(1u << d);
        cells[best_idx] = d;
        row_m[r] |= bit;
        col_m[c] |= bit;
        box_m[bx] |= bit;
        search();
        cells[best_idx] = 0;
        row_m[r] &= ~bit;
        col_m[c] &= ~bit;
        box_m[bx] &= ~bit;
        if (solutions >= limit)
          return;
      }
    }
  }
};

// ---------------------------------------------------------------------------
// Helpers for analyze_difficulty
// ---------------------------------------------------------------------------
inline uint16_t compute_candidates(const Board &b, int idx) noexcept {
  const int r = idx / 9, c = idx % 9, bx = box_of(idx);
  uint16_t used = 0;
  for (int k = 0; k < 9; ++k) {
    const int32_t vr = b[r * 9 + k];
    if (vr > 0)
      used |= static_cast<uint16_t>(1u << vr);
    const int32_t vc = b[k * 9 + c];
    if (vc > 0)
      used |= static_cast<uint16_t>(1u << vc);
  }
  const int br = (bx / 3) * 3, bc = (bx % 3) * 3;
  for (int dr = 0; dr < 3; ++dr)
    for (int dc = 0; dc < 3; ++dc) {
      const int32_t v = b[(br + dr) * 9 + (bc + dc)];
      if (v > 0)
        used |= static_cast<uint16_t>(1u << v);
    }
  return static_cast<uint16_t>((~used) & kAllDigits);
}

// type: 0=row, 1=col, 2=box. u = unit index (0..8), p = position (0..8).
inline int unit_index(int type, int u, int p) noexcept {
  if (type == 0)
    return u * 9 + p;
  if (type == 1)
    return p * 9 + u;
  const int br = (u / 3) * 3, bc = (u % 3) * 3;
  return (br + p / 3) * 9 + (bc + p % 3);
}

// Convert user-facing board (<=0 == empty) into internal (0 == empty),
// rejecting out-of-range values.
Board normalize(const Board &in) {
  Board out{};
  for (int i = 0; i < kCells; ++i) {
    const int32_t v = in[i];
    if (v > 9)
      throw std::invalid_argument(
          "sudoku values must be in [1, 9] or <= 0 for empty");
    out[i] = (v >= 1 && v <= 9) ? v : 0;
  }
  return out;
}

int count_solutions_internal(const Board &norm, int limit) {
  FastSolver s;
  if (!s.load(norm))
    throw std::invalid_argument("sudoku has duplicate digits");
  s.limit = limit;
  s.search();
  return s.solutions;
}

// One generation attempt: random solved grid, then dig holes keeping
// uniqueness.
std::optional<Board> generate_one(std::mt19937 &rng, int target_removed) {
  FastSolver fill;
  fill.randomize = true;
  fill.rng = &rng;
  fill.limit = 1;
  fill.search();
  if (fill.solutions == 0)
    return std::nullopt;

  Board board = fill.solution;

  std::array<int, kCells> order;
  std::iota(order.begin(), order.end(), 0);
  std::shuffle(order.begin(), order.end(), rng);

  int removed = 0;
  for (int pos : order) {
    if (removed >= target_removed)
      break;
    const int32_t save = board[pos];
    board[pos] = 0;
    if (count_solutions_internal(board, 2) == 1) {
      ++removed;
    } else {
      board[pos] = save;
    }
  }

  if (removed < target_removed)
    return std::nullopt;
  return board;
}

} // namespace

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------
Board solve(const Board &puzzle) {
  const Board norm = normalize(puzzle);
  FastSolver s;
  if (!s.load(norm))
    throw std::invalid_argument("sudoku has duplicate digits");
  s.limit = 1;
  s.search();
  if (s.solutions == 0)
    throw std::runtime_error("sudoku has no solution");
  return s.solution;
}

bool has_unique_solution(const Board &puzzle) {
  return count_solutions_internal(normalize(puzzle), 2) == 1;
}

int count_solutions(const Board &puzzle, int limit) {
  if (limit < 1)
    throw std::invalid_argument("limit must be >= 1");
  return count_solutions_internal(normalize(puzzle), limit);
}

Board create_puzzle(uint32_t known_numbers) {
  if (known_numbers < static_cast<uint32_t>(kMinGivens) ||
      known_numbers > static_cast<uint32_t>(kMaxGivens)) {
    throw std::invalid_argument("known_numbers must be in [17, 81]");
  }
  const int target_removed = kCells - static_cast<int>(known_numbers);

  if (target_removed == 0) {
    FastSolver fill;
    std::mt19937 rng{std::random_device{}()};
    fill.randomize = true;
    fill.rng = &rng;
    fill.limit = 1;
    fill.search();
    return fill.solution;
  }

  std::atomic<bool> found{false};
  Board result{};

  int nthreads = 1;
#ifdef _OPENMP
  nthreads = omp_get_max_threads();
#endif
  const auto deadline =
      std::chrono::steady_clock::now() + std::chrono::seconds(3);

#pragma omp parallel num_threads(nthreads)
  {
    std::mt19937 rng;
#ifdef _OPENMP
    rng.seed(std::random_device{}() ^
             (static_cast<uint32_t>(omp_get_thread_num()) * 0x9E3779B9u));
#else
    rng.seed(std::random_device{}());
#endif

    for (;;) {
      if (found.load(std::memory_order_relaxed))
        break;
      if (std::chrono::steady_clock::now() > deadline)
        break;

      auto p = generate_one(rng, target_removed);
      if (p.has_value()) {
        bool expected = false;
        if (found.compare_exchange_strong(expected, true)) {
          result = *p;
        }
        break;
      }
    }
  }

  if (!found.load(std::memory_order_relaxed)) {
    throw std::runtime_error(
        "could not generate a sudoku with the requested number of givens "
        "(try a larger value; practical minimum for this generator is ~22-24)");
  }
  return result;
}

bool is_solved(const Board &board) {
  std::array<uint16_t, 9> rows{}, cols{}, boxes{};
  for (int i = 0; i < kCells; ++i) {
    const int32_t v = board[i];
    if (v < 1 || v > 9)
      return false;
    const uint16_t bit = static_cast<uint16_t>(1u << v);
    const int r = i / 9, c = i % 9, bx = box_of(i);
    if ((rows[r] | cols[c] | boxes[bx]) & bit)
      return false;
    rows[r] |= bit;
    cols[c] |= bit;
    boxes[bx] |= bit;
  }
  return true;
}

bool is_consistent(const Board &puzzle) {
  std::array<uint16_t, 9> rows{}, cols{}, boxes{};
  for (int i = 0; i < kCells; ++i) {
    const int32_t v = puzzle[i];
    if (v <= 0)
      continue;
    if (v > 9)
      return false;
    const uint16_t bit = static_cast<uint16_t>(1u << v);
    const int r = i / 9, c = i % 9, bx = box_of(i);
    if ((rows[r] | cols[c] | boxes[bx]) & bit)
      return false;
    rows[r] |= bit;
    cols[c] |= bit;
    boxes[bx] |= bit;
  }
  return true;
}

std::array<double, kCells> analyze_difficulty(const Board &puzzle) {
  const Board norm = normalize(puzzle);
  if (!is_consistent(norm))
    throw std::invalid_argument("sudoku has duplicate digits");

  Board work = norm;
  std::array<int, kCells>  rounds{};
  std::array<bool, kCells> was_hidden{};
  rounds.fill(-1);

  int empty_count = 0;
  for (int i = 0; i < kCells; ++i)
    if (work[i] == 0)
      ++empty_count;

  int round = 0;
  while (empty_count > 0) {
    std::array<uint16_t, kCells> cand{};
    for (int i = 0; i < kCells; ++i)
      if (work[i] == 0)
        cand[i] = compute_candidates(work, i);

    std::array<bool, kCells> to_fill{};
    std::array<int, kCells>  fill_value{};
    std::array<bool, kCells> fill_hidden{};
    bool any = false;

    // 1) Naked singles (1 candidate) take precedence over hidden.
    for (int i = 0; i < kCells; ++i) {
      if (work[i] != 0)
        continue;
      if (std::popcount(cand[i]) == 1) {
        to_fill[i]     = true;
        fill_value[i]  = std::countr_zero(cand[i]);
        fill_hidden[i] = false;
        any = true;
      }
    }

    // 2) Hidden singles: digit d can go in exactly one cell of a unit.
    for (int type = 0; type < 3; ++type) {
      for (int u = 0; u < 9; ++u) {
        for (int d = 1; d <= 9; ++d) {
          bool d_present = false;
          int only_idx = -1, count = 0;
          for (int p = 0; p < 9; ++p) {
            const int idx = unit_index(type, u, p);
            const int32_t v = work[idx];
            if (v == d) { d_present = true; break; }
            if (v == 0 && (cand[idx] & (1u << d))) {
              ++count;
              only_idx = idx;
            }
          }
          if (d_present || count != 1)
            continue;
          if (to_fill[only_idx])
            continue; // naked single wins
          to_fill[only_idx]     = true;
          fill_value[only_idx]  = d;
          fill_hidden[only_idx] = true;
          any = true;
        }
      }
    }

    if (!any)
      break;

    for (int i = 0; i < kCells; ++i) {
      if (!to_fill[i])
        continue;
      work[i]       = fill_value[i];
      rounds[i]     = round;
      was_hidden[i] = fill_hidden[i];
      --empty_count;
    }
    ++round;
  }

  const int max_round = round - 1;

  std::array<double, kCells> scores{};
  for (int i = 0; i < kCells; ++i) {
    if (norm[i] != 0) {
      scores[i] = std::numeric_limits<double>::quiet_NaN();
      continue;
    }
    if (rounds[i] < 0) {
      // Needs guessing. Fewer end-state candidates = slightly easier.
      const int nc = std::popcount(compute_candidates(work, i));
      if (nc == 0) {
        scores[i] = 1.0;
        continue;
      }
      const double t = std::clamp((nc - 2) / 7.0, 0.0, 1.0);
      scores[i] = 0.85 + 0.15 * t;
      continue;
    }
    const double r_norm = (max_round <= 0)
        ? 0.0
        : static_cast<double>(rounds[i]) / max_round;
    double base = 0.10 + 0.65 * r_norm;
    if (was_hidden[i])
      base += 0.05;
    scores[i] = std::min(base, 0.84);
  }
  return scores;
}

} // namespace sudoku
