#include "ternary_cover.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <bit>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <mutex>
#include <random>
#include <string>
#include <thread>
#include <tuple>
#include <unordered_set>
#include <vector>

namespace {

constexpr int kSuperCenters = 18;
constexpr int kProjectedCenters = 16;
constexpr int kTopMoves = 32;
constexpr int kStructuralTopMoves = 64;

struct Options {
    int seconds = 60;
    int threads = 0;
    int max_elites = 500;
    int elite_threshold = 7;
    std::uint64_t seed = 1;
    bool evaluate_only = false;
    std::string start_path = "data/seed_18_supercode.txt";
    std::string output_path = "search-results/compressed_best_16.txt";
    std::string elite_directory = "search-results/compression-elites";
};

int parse_int(const char* text, const char* name) {
    try {
        std::size_t consumed = 0;
        const int value = std::stoi(text, &consumed);
        if (text[consumed] != '\0') {
            throw std::invalid_argument("trailing characters");
        }
        return value;
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("invalid ") + name);
    }
}

std::uint64_t parse_u64(const char* text, const char* name) {
    try {
        std::size_t consumed = 0;
        const std::uint64_t value = std::stoull(text, &consumed);
        if (text[consumed] != '\0') {
            throw std::invalid_argument("trailing characters");
        }
        return value;
    } catch (const std::exception&) {
        throw std::invalid_argument(std::string("invalid ") + name);
    }
}

Options parse_options(int argc, char** argv) {
    Options options;
    for (int i = 1; i < argc; ++i) {
        const std::string argument = argv[i];
        auto require_value = [&]() -> const char* {
            if (i + 1 >= argc) {
                throw std::invalid_argument(
                    "missing value after " + argument);
            }
            return argv[++i];
        };

        if (argument == "--seconds") {
            options.seconds = parse_int(require_value(), "time limit");
        } else if (argument == "--threads") {
            options.threads = parse_int(require_value(), "thread count");
        } else if (argument == "--seed") {
            options.seed = parse_u64(require_value(), "seed");
        } else if (argument == "--start") {
            options.start_path = require_value();
        } else if (argument == "--output") {
            options.output_path = require_value();
        } else if (argument == "--elite-dir") {
            options.elite_directory = require_value();
        } else if (argument == "--max-elites") {
            options.max_elites =
                parse_int(require_value(), "maximum elite count");
        } else if (argument == "--elite-threshold") {
            options.elite_threshold =
                parse_int(require_value(), "elite threshold");
        } else if (argument == "--evaluate-only") {
            options.evaluate_only = true;
        } else if (argument == "--help") {
            std::cout
                << "usage: compress_code [options]\n"
                << "  --seconds N          wall-clock limit, default 60\n"
                << "  --threads N          worker count\n"
                << "  --seed N             base random seed\n"
                << "  --start PATH         16- or 18-center seed\n"
                << "  --output PATH        best 16-center projection\n"
                << "  --elite-dir PATH     distinct near-cover directory\n"
                << "  --max-elites N       maximum saved elites\n"
                << "  --elite-threshold N  largest saved hole count\n"
                << "  --evaluate-only      score the seed and exit\n";
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }

    if (options.seconds <= 0) {
        throw std::invalid_argument("time limit must be positive");
    }
    if (options.threads <= 0) {
        options.threads = static_cast<int>(
            std::max(1u, std::thread::hardware_concurrency()));
    }
    if (options.max_elites < 0 || options.elite_threshold < 0) {
        throw std::invalid_argument(
            "elite limits must be nonnegative");
    }
    return options;
}

struct BucketStats {
    int zero = 0;
    std::int64_t weighted_zero = 0;
    std::array<int, kSuperCenters> one{};
    std::array<std::int64_t, kSuperCenters> weighted_one{};
    std::array<std::array<int, kSuperCenters>, kSuperCenters> two{};
    std::array<
        std::array<std::int64_t, kSuperCenters>,
        kSuperCenters> weighted_two{};

    void adjust(
        std::uint32_t support,
        std::uint32_t weight,
        int direction) {
        const int count = std::popcount(support);
        if (count == 0) {
            zero += direction;
            weighted_zero +=
                static_cast<std::int64_t>(direction) * weight;
        } else if (count == 1) {
            const int first = std::countr_zero(support);
            one[static_cast<std::size_t>(first)] += direction;
            weighted_one[static_cast<std::size_t>(first)] +=
                static_cast<std::int64_t>(direction) * weight;
        } else if (count == 2) {
            const int first = std::countr_zero(support);
            support &= support - 1;
            const int second = std::countr_zero(support);
            two[static_cast<std::size_t>(first)]
               [static_cast<std::size_t>(second)] += direction;
            weighted_two[static_cast<std::size_t>(first)]
                        [static_cast<std::size_t>(second)] +=
                static_cast<std::int64_t>(direction) * weight;
        }
    }

    void adjust_weight(std::uint32_t support, int delta) {
        const int count = std::popcount(support);
        if (count == 0) {
            weighted_zero += delta;
        } else if (count == 1) {
            const int first = std::countr_zero(support);
            weighted_one[static_cast<std::size_t>(first)] += delta;
        } else if (count == 2) {
            const int first = std::countr_zero(support);
            support &= support - 1;
            const int second = std::countr_zero(support);
            weighted_two[static_cast<std::size_t>(first)]
                        [static_cast<std::size_t>(second)] += delta;
        }
    }
};

struct Projection {
    std::int64_t weighted_holes =
        std::numeric_limits<std::int64_t>::max();
    int holes = ternary_cover::kSpaceSize;
    int first = 0;
    int second = 1;
};

bool better_projection(const Projection& lhs, const Projection& rhs) {
    return std::tie(
               lhs.weighted_holes,
               lhs.holes,
               lhs.first,
               lhs.second) <
           std::tie(
               rhs.weighted_holes,
               rhs.holes,
               rhs.first,
               rhs.second);
}

Projection best_projection(const BucketStats& stats) {
    Projection best;
    for (int first = 0; first < kSuperCenters; ++first) {
        for (int second = first + 1;
             second < kSuperCenters;
             ++second) {
            Projection candidate;
            candidate.first = first;
            candidate.second = second;
            candidate.holes =
                stats.zero +
                stats.one[static_cast<std::size_t>(first)] +
                stats.one[static_cast<std::size_t>(second)] +
                stats.two[static_cast<std::size_t>(first)]
                         [static_cast<std::size_t>(second)];
            candidate.weighted_holes =
                stats.weighted_zero +
                stats.weighted_one[static_cast<std::size_t>(first)] +
                stats.weighted_one[static_cast<std::size_t>(second)] +
                stats.weighted_two[static_cast<std::size_t>(first)]
                                  [static_cast<std::size_t>(second)];
            if (better_projection(candidate, best)) {
                best = candidate;
            }
        }
    }
    return best;
}

struct SearchState {
    std::array<int, kSuperCenters> centers{};
    std::array<int, ternary_cover::kSpaceSize> position{};
    std::array<std::uint32_t, ternary_cover::kSpaceSize> support{};
    std::array<std::uint32_t, ternary_cover::kSpaceSize> weights{};
    std::array<int, ternary_cover::kSpaceSize> tabu_until{};
    BucketStats buckets;

    SearchState(
        const ternary_cover::Geometry& geometry,
        const std::vector<int>& seed) {
        if (seed.size() != kSuperCenters) {
            throw std::invalid_argument(
                "compression state requires exactly 18 centers");
        }
        position.fill(-1);
        weights.fill(1);
        tabu_until.fill(0);
        for (int slot = 0; slot < kSuperCenters; ++slot) {
            const int center = seed[static_cast<std::size_t>(slot)];
            if (position[static_cast<std::size_t>(center)] != -1) {
                throw std::invalid_argument(
                    "compression seed contains duplicate centers");
            }
            centers[static_cast<std::size_t>(slot)] = center;
            position[static_cast<std::size_t>(center)] = slot;
            const std::uint32_t bit = 1u << slot;
            for (int point :
                 geometry.balls[static_cast<std::size_t>(center)]) {
                support[static_cast<std::size_t>(point)] |= bit;
            }
        }
        for (int point = 0;
             point < ternary_cover::kSpaceSize;
             ++point) {
            buckets.adjust(
                support[static_cast<std::size_t>(point)],
                weights[static_cast<std::size_t>(point)],
                1);
        }
    }
};

template <class Callback>
void for_changed_points(
    const ternary_cover::Geometry& geometry,
    int old_center,
    int new_center,
    Callback callback) {
    const auto& old_ball =
        geometry.balls[static_cast<std::size_t>(old_center)];
    const auto& new_ball =
        geometry.balls[static_cast<std::size_t>(new_center)];
    int old_index = 0;
    int new_index = 0;
    while (old_index < ternary_cover::kBallSize ||
           new_index < ternary_cover::kBallSize) {
        if (new_index == ternary_cover::kBallSize ||
            (old_index < ternary_cover::kBallSize &&
             old_ball[static_cast<std::size_t>(old_index)] <
                 new_ball[static_cast<std::size_t>(new_index)])) {
            callback(
                old_ball[static_cast<std::size_t>(old_index)],
                false);
            ++old_index;
        } else if (
            old_index == ternary_cover::kBallSize ||
            new_ball[static_cast<std::size_t>(new_index)] <
                old_ball[static_cast<std::size_t>(old_index)]) {
            callback(
                new_ball[static_cast<std::size_t>(new_index)],
                true);
            ++new_index;
        } else {
            ++old_index;
            ++new_index;
        }
    }
}

Projection evaluate_exchange(
    const ternary_cover::Geometry& geometry,
    const SearchState& state,
    int slot,
    int new_center) {
    BucketStats candidate = state.buckets;
    const int old_center =
        state.centers[static_cast<std::size_t>(slot)];
    const std::uint32_t bit = 1u << slot;
    for_changed_points(
        geometry,
        old_center,
        new_center,
        [&](int point, bool added) {
            const std::uint32_t old_support =
                state.support[static_cast<std::size_t>(point)];
            const std::uint32_t new_support =
                added ? old_support | bit : old_support & ~bit;
            const std::uint32_t weight =
                state.weights[static_cast<std::size_t>(point)];
            candidate.adjust(old_support, weight, -1);
            candidate.adjust(new_support, weight, 1);
        });
    return best_projection(candidate);
}

void apply_exchange(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    int slot,
    int new_center) {
    const int old_center =
        state.centers[static_cast<std::size_t>(slot)];
    const std::uint32_t bit = 1u << slot;
    for_changed_points(
        geometry,
        old_center,
        new_center,
        [&](int point, bool added) {
            std::uint32_t& support =
                state.support[static_cast<std::size_t>(point)];
            const std::uint32_t weight =
                state.weights[static_cast<std::size_t>(point)];
            state.buckets.adjust(support, weight, -1);
            support = added ? support | bit : support & ~bit;
            state.buckets.adjust(support, weight, 1);
        });
    state.position[static_cast<std::size_t>(old_center)] = -1;
    state.position[static_cast<std::size_t>(new_center)] = slot;
    state.centers[static_cast<std::size_t>(slot)] = new_center;
}

std::vector<int> projected_centers(
    const SearchState& state,
    const Projection& projection) {
    std::vector<int> result;
    result.reserve(kProjectedCenters);
    for (int slot = 0; slot < kSuperCenters; ++slot) {
        if (slot != projection.first && slot != projection.second) {
            result.push_back(
                state.centers[static_cast<std::size_t>(slot)]);
        }
    }
    std::sort(result.begin(), result.end());
    return result;
}

std::vector<int> projected_holes(
    const SearchState& state,
    const Projection& projection) {
    const std::uint32_t deleted =
        (1u << projection.first) | (1u << projection.second);
    std::vector<int> holes;
    holes.reserve(static_cast<std::size_t>(projection.holes));
    for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
        if ((state.support[static_cast<std::size_t>(point)] & ~deleted) == 0) {
            holes.push_back(point);
        }
    }
    return holes;
}

int choose_hole(
    const SearchState& state,
    const std::vector<int>& holes,
    std::mt19937_64& rng) {
    std::uint64_t total = 0;
    for (int point : holes) {
        total += state.weights[static_cast<std::size_t>(point)];
    }
    std::uniform_int_distribution<std::uint64_t> distribution(1, total);
    std::uint64_t target = distribution(rng);
    for (int point : holes) {
        const std::uint32_t weight =
            state.weights[static_cast<std::size_t>(point)];
        if (target <= weight) {
            return point;
        }
        target -= weight;
    }
    return holes.back();
}

void increase_hole_weights(
    SearchState& state,
    const std::vector<int>& holes) {
    for (int point : holes) {
        std::uint32_t& weight =
            state.weights[static_cast<std::size_t>(point)];
        if (weight == 1000000) {
            continue;
        }
        ++weight;
        state.buckets.adjust_weight(
            state.support[static_cast<std::size_t>(point)],
            1);
    }
}

struct Move {
    int slot = -1;
    int new_center = -1;
    Projection projection;
    int four_violations = std::numeric_limits<int>::max();
    std::uint64_t tie_break = 0;
};

bool better_move(const Move& lhs, const Move& rhs) {
    return std::tie(
               lhs.projection.weighted_holes,
               lhs.projection.holes,
               lhs.tie_break) <
           std::tie(
               rhs.projection.weighted_holes,
               rhs.projection.holes,
               rhs.tie_break);
}

std::vector<Move> ranked_moves(
    const ternary_cover::Geometry& geometry,
    const SearchState& state,
    int hole,
    int iteration,
    int aspiration_holes,
    int move_limit,
    std::mt19937_64& rng) {
    std::vector<Move> moves;
    moves.reserve(
        ternary_cover::kBallSize *
        static_cast<std::size_t>(kSuperCenters));
    for (int new_center :
         geometry.balls[static_cast<std::size_t>(hole)]) {
        if (state.position[static_cast<std::size_t>(new_center)] != -1) {
            continue;
        }
        for (int slot = 0; slot < kSuperCenters; ++slot) {
            Move move;
            move.slot = slot;
            move.new_center = new_center;
            move.projection =
                evaluate_exchange(geometry, state, slot, new_center);
            move.tie_break = rng();
            const bool tabu =
                state.tabu_until[static_cast<std::size_t>(new_center)] >
                iteration;
            if (tabu && move.projection.holes >= aspiration_holes) {
                continue;
            }
            moves.push_back(move);
        }
    }
    std::sort(moves.begin(), moves.end(), better_move);
    if (moves.size() > static_cast<std::size_t>(move_limit)) {
        moves.resize(static_cast<std::size_t>(move_limit));
    }
    return moves;
}

std::size_t choose_rank(
    std::size_t count,
    int stagnation,
    std::mt19937_64& rng) {
    if (count <= 1) {
        return 0;
    }
    const int continuation = std::min(80, 25 + stagnation / 30);
    std::size_t rank = 0;
    std::uniform_int_distribution<int> percent(0, 99);
    while (rank + 1 < count && percent(rng) < continuation) {
        ++rank;
    }
    return rank;
}

int four_projection_violations(const std::vector<int>& centers) {
    int violations = 0;
    for (int first = 0; first < ternary_cover::kLength; ++first) {
        for (int second = first + 1;
             second < ternary_cover::kLength;
             ++second) {
            for (int third = second + 1;
                 third < ternary_cover::kLength;
                 ++third) {
                for (int fourth = third + 1;
                     fourth < ternary_cover::kLength;
                     ++fourth) {
                    const std::array<int, 4> coordinates{
                        first, second, third, fourth};
                    for (int pattern = 0; pattern < 81; ++pattern) {
                        int value = pattern;
                        std::array<int, 4> symbols{};
                        for (int index = 3; index >= 0; --index) {
                            symbols[static_cast<std::size_t>(index)] =
                                value % 3;
                            value /= 3;
                        }
                        std::array<int, 3> distance_counts{};
                        for (int center : centers) {
                            const auto digits =
                                ternary_cover::decode(center);
                            int distance = 0;
                            for (int index = 0; index < 4; ++index) {
                                distance +=
                                    digits[static_cast<std::size_t>(
                                        coordinates[
                                            static_cast<std::size_t>(
                                                index)])] !=
                                    symbols[static_cast<std::size_t>(index)];
                            }
                            if (distance <= 2) {
                                ++distance_counts[
                                    static_cast<std::size_t>(distance)];
                            }
                        }
                        if (9 * distance_counts[0] +
                                5 * distance_counts[1] +
                                distance_counts[2] <
                            9) {
                            ++violations;
                        }
                    }
                }
            }
        }
    }
    return violations;
}

int move_four_violations(
    const ternary_cover::Geometry& geometry,
    const SearchState& state,
    const Move& move) {
    SearchState candidate = state;
    apply_exchange(
        geometry,
        candidate,
        move.slot,
        move.new_center);
    return four_projection_violations(
        projected_centers(candidate, move.projection));
}

bool better_structural_move(const Move& lhs, const Move& rhs) {
    const int lhs_score =
        8 * lhs.projection.holes + lhs.four_violations;
    const int rhs_score =
        8 * rhs.projection.holes + rhs.four_violations;
    return std::tie(
               lhs_score,
               lhs.four_violations,
               lhs.projection.weighted_holes,
               lhs.tie_break) <
           std::tie(
               rhs_score,
               rhs.four_violations,
               rhs.projection.weighted_holes,
               rhs.tie_break);
}

std::uint64_t code_hash(const std::vector<int>& centers) {
    std::uint64_t hash = 1469598103934665603ull;
    for (int center : centers) {
        hash ^= static_cast<std::uint64_t>(center + 1);
        hash *= 1099511628211ull;
    }
    return hash;
}

struct SharedBest {
    std::atomic<bool> found{false};
    std::atomic<int> holes{ternary_cover::kSpaceSize};
    std::atomic<int> four_violations{std::numeric_limits<int>::max()};
    std::atomic<std::uint64_t> steps{0};
    std::mutex mutex;
    std::vector<int> centers;
    std::unordered_set<std::uint64_t> elite_hashes;
};

void write_code_with_directories(
    const std::string& path,
    const std::vector<int>& centers) {
    const std::filesystem::path output(path);
    if (output.has_parent_path()) {
        std::filesystem::create_directories(output.parent_path());
    }
    ternary_cover::write_code(path, centers);
}

void report_candidate(
    const Options& options,
    const ternary_cover::Geometry& geometry,
    const SearchState& state,
    const Projection& projection,
    SharedBest& shared) {
    const int observed_holes =
        shared.holes.load(std::memory_order_relaxed);
    if (projection.holes > observed_holes &&
        projection.holes > options.elite_threshold) {
        return;
    }

    const std::vector<int> centers =
        projected_centers(state, projection);
    const auto verification =
        ternary_cover::verify_code(geometry, centers);
    if (verification.holes != projection.holes ||
        !verification.distinct) {
        throw std::logic_error(
            "compression projection failed direct verification");
    }
    const int violations = four_projection_violations(centers);
    const std::uint64_t hash = code_hash(centers);

    std::lock_guard<std::mutex> lock(shared.mutex);
    const int best_holes =
        shared.holes.load(std::memory_order_relaxed);
    const int best_violations =
        shared.four_violations.load(std::memory_order_relaxed);
    if (projection.holes < best_holes ||
        (projection.holes == best_holes &&
         violations < best_violations)) {
        shared.holes.store(projection.holes, std::memory_order_relaxed);
        shared.four_violations.store(
            violations, std::memory_order_relaxed);
        shared.centers = centers;
        write_code_with_directories(options.output_path, centers);
    }

    if (projection.holes <= options.elite_threshold &&
        static_cast<int>(shared.elite_hashes.size()) <
            options.max_elites &&
        shared.elite_hashes.insert(hash).second) {
        const std::filesystem::path directory(options.elite_directory);
        std::filesystem::create_directories(directory);
        const std::string filename =
            "h" + std::to_string(projection.holes) +
            "_v" + std::to_string(violations) +
            "_" + std::to_string(hash) + ".txt";
        ternary_cover::write_code((directory / filename).string(), centers);
    }

    if (projection.holes == 0) {
        shared.found.store(true, std::memory_order_relaxed);
    }
}

std::vector<int> augment_seed(
    const ternary_cover::Geometry& geometry,
    const std::vector<int>& seed) {
    if (seed.size() == kSuperCenters) {
        return seed;
    }
    if (seed.size() != kProjectedCenters) {
        throw std::invalid_argument(
            "compression seed must contain 16 or 18 centers");
    }

    std::array<bool, ternary_cover::kSpaceSize> selected{};
    std::array<int, ternary_cover::kSpaceSize> multiplicity{};
    for (int center : seed) {
        if (selected[static_cast<std::size_t>(center)]) {
            throw std::invalid_argument("seed contains duplicate centers");
        }
        selected[static_cast<std::size_t>(center)] = true;
        for (int point :
             geometry.balls[static_cast<std::size_t>(center)]) {
            ++multiplicity[static_cast<std::size_t>(point)];
        }
    }

    ternary_cover::Mask holes;
    ternary_cover::Mask singles;
    for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
        if (multiplicity[static_cast<std::size_t>(point)] == 0) {
            holes.set(static_cast<std::size_t>(point));
        } else if (multiplicity[static_cast<std::size_t>(point)] == 1) {
            singles.set(static_cast<std::size_t>(point));
        }
    }

    int best_first = -1;
    int best_second = -1;
    int best_holes = -1;
    int best_singles = -1;
    for (int first = 0; first < ternary_cover::kSpaceSize; ++first) {
        if (selected[static_cast<std::size_t>(first)]) {
            continue;
        }
        for (int second = first + 1;
             second < ternary_cover::kSpaceSize;
             ++second) {
            if (selected[static_cast<std::size_t>(second)]) {
                continue;
            }
            const auto added =
                geometry.masks[static_cast<std::size_t>(first)] |
                geometry.masks[static_cast<std::size_t>(second)];
            const int holes_covered =
                static_cast<int>((added & holes).count());
            const int singles_reinforced =
                static_cast<int>((added & singles).count());
            if (std::tie(holes_covered, singles_reinforced) >
                std::tie(best_holes, best_singles)) {
                best_first = first;
                best_second = second;
                best_holes = holes_covered;
                best_singles = singles_reinforced;
            }
        }
    }
    if (best_first < 0 || best_second < 0) {
        throw std::logic_error("failed to augment the compression seed");
    }

    std::vector<int> result = seed;
    result.push_back(best_first);
    result.push_back(best_second);
    return result;
}

void random_perturbation(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    int moves,
    std::mt19937_64& rng) {
    std::uniform_int_distribution<int> slot_distribution(
        0, kSuperCenters - 1);
    std::uniform_int_distribution<int> center_distribution(
        0, ternary_cover::kSpaceSize - 1);
    for (int move = 0; move < moves; ++move) {
        int new_center = center_distribution(rng);
        while (state.position[static_cast<std::size_t>(new_center)] != -1) {
            new_center = center_distribution(rng);
        }
        apply_exchange(
            geometry,
            state,
            slot_distribution(rng),
            new_center);
    }
}

void worker(
    int worker_id,
    const Options& options,
    const ternary_cover::Geometry& geometry,
    const std::vector<int>& seed,
    std::chrono::steady_clock::time_point deadline,
    SharedBest& shared) {
    std::seed_seq seed_sequence{
        static_cast<std::uint32_t>(options.seed),
        static_cast<std::uint32_t>(options.seed >> 32),
        static_cast<std::uint32_t>(worker_id),
        0x1831602u};
    std::mt19937_64 rng(seed_sequence);
    std::uint64_t local_steps = 0;
    int restart = 0;

    while (!shared.found.load(std::memory_order_relaxed) &&
           std::chrono::steady_clock::now() < deadline) {
        SearchState state(geometry, seed);
        if (restart > 0) {
            random_perturbation(
                geometry,
                state,
                2 + (restart + worker_id) % 7,
                rng);
        }

        Projection current = best_projection(state.buckets);
        report_candidate(options, geometry, state, current, shared);
        int local_best = current.holes;
        int stagnation = 0;
        const int restart_limit = 8000 + 250 * (worker_id % 11);

        for (int iteration = 1;
             iteration <= restart_limit &&
             !shared.found.load(std::memory_order_relaxed) &&
             std::chrono::steady_clock::now() < deadline;
             ++iteration) {
            if (current.holes == 0) {
                report_candidate(
                    options, geometry, state, current, shared);
                break;
            }

            std::vector<int> holes = projected_holes(state, current);
            if (iteration % 20 == 0) {
                increase_hole_weights(state, holes);
                current = best_projection(state.buckets);
                holes = projected_holes(state, current);
            }
            const int hole = choose_hole(state, holes, rng);
            const int aspiration =
                shared.holes.load(std::memory_order_relaxed);
            const bool structural_mode =
                stagnation >= 100 && iteration % 25 == 0;
            std::vector<Move> moves = ranked_moves(
                geometry,
                state,
                hole,
                iteration,
                aspiration,
                structural_mode
                    ? kStructuralTopMoves
                    : kTopMoves,
                rng);
            if (moves.empty()) {
                random_perturbation(geometry, state, 3, rng);
                current = best_projection(state.buckets);
                stagnation += 3;
                local_steps += 3;
                continue;
            }
            if (structural_mode) {
                for (Move& move : moves) {
                    move.four_violations =
                        move_four_violations(geometry, state, move);
                }
                std::sort(
                    moves.begin(),
                    moves.end(),
                    better_structural_move);
            }

            const int allowance = std::min(9, 1 + stagnation / 120);
            std::vector<Move> eligible_moves;
            eligible_moves.reserve(moves.size());
            for (const Move& move : moves) {
                if (move.projection.holes <=
                    current.holes + allowance) {
                    eligible_moves.push_back(move);
                }
            }
            if (eligible_moves.empty()) {
                eligible_moves.push_back(moves.front());
            }
            const std::size_t rank =
                choose_rank(eligible_moves.size(), stagnation, rng);
            const Move chosen = eligible_moves[rank];
            const int removed =
                state.centers[static_cast<std::size_t>(chosen.slot)];
            apply_exchange(
                geometry,
                state,
                chosen.slot,
                chosen.new_center);
            state.tabu_until[static_cast<std::size_t>(removed)] =
                iteration + 7 + static_cast<int>(rng() % 17);
            current = chosen.projection;
            ++local_steps;

            if (current.holes < local_best) {
                local_best = current.holes;
                stagnation = 0;
            } else {
                ++stagnation;
            }
            if (current.holes <= std::max(
                    shared.holes.load(std::memory_order_relaxed),
                    options.elite_threshold)) {
                report_candidate(
                    options, geometry, state, current, shared);
            }
            if (stagnation > 0 && stagnation % 600 == 0) {
                random_perturbation(
                    geometry,
                    state,
                    3 + static_cast<int>(rng() % 5),
                    rng);
                current = best_projection(state.buckets);
                local_steps += 3;
            }
        }
        ++restart;
    }
    shared.steps.fetch_add(local_steps, std::memory_order_relaxed);
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const ternary_cover::Geometry geometry;
        const std::vector<int> input =
            ternary_cover::read_code(options.start_path);
        const std::vector<int> seed = augment_seed(geometry, input);
        SearchState initial(geometry, seed);
        const Projection projection = best_projection(initial.buckets);

        if (options.evaluate_only) {
            const std::vector<int> centers =
                projected_centers(initial, projection);
            const auto verification =
                ternary_cover::verify_code(geometry, centers);
            if (
                !verification.distinct
                || verification.holes != projection.holes
            ) {
                throw std::logic_error(
                    "compression projection failed direct verification");
            }
            write_code_with_directories(options.output_path, centers);
            std::cout << "supercode centers: " << seed.size() << '\n';
            std::cout << "supercode holes: "
                      << initial.buckets.zero << '\n';
            std::cout << "best projected holes: "
                      << projection.holes << '\n';
            std::cout << "four-coordinate violations: "
                      << four_projection_violations(centers) << '\n';
            std::cout << "deleted slots: "
                      << projection.first << ' '
                      << projection.second << '\n';
            return 0;
        }

        SharedBest shared;
        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::seconds(options.seconds);
        std::vector<std::thread> workers;
        workers.reserve(static_cast<std::size_t>(options.threads));
        for (int worker_id = 0;
             worker_id < options.threads;
             ++worker_id) {
            workers.emplace_back(
                worker,
                worker_id,
                std::cref(options),
                std::cref(geometry),
                std::cref(seed),
                deadline,
                std::ref(shared));
        }
        for (std::thread& thread : workers) {
            thread.join();
        }

        std::cout << "workers: " << options.threads << '\n';
        std::cout << "steps: "
                  << shared.steps.load(std::memory_order_relaxed) << '\n';
        std::cout << "best holes: "
                  << shared.holes.load(std::memory_order_relaxed) << '\n';
        std::cout << "four-coordinate violations: "
                  << shared.four_violations.load(
                         std::memory_order_relaxed)
                  << '\n';
        std::cout << "saved elites: " << shared.elite_hashes.size() << '\n';
        std::cout << "best code: " << options.output_path << '\n';
        std::cout << "cover found: "
                  << (shared.found.load(std::memory_order_relaxed)
                          ? "yes"
                          : "no")
                  << '\n';
        return shared.found.load(std::memory_order_relaxed) ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
