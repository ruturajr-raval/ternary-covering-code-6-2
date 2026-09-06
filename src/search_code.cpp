#include "ternary_cover.hpp"

#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <mutex>
#include <numeric>
#include <optional>
#include <random>
#include <string>
#include <thread>
#include <vector>

namespace {

struct Options {
    int centers = 16;
    int seconds = 60;
    int threads = 0;
    std::uint64_t seed = 1;
    std::string start_path;
    std::string output_path = "search-results/best_code.txt";
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

        if (argument == "--centers") {
            options.centers = parse_int(require_value(), "center count");
        } else if (argument == "--seconds") {
            options.seconds = parse_int(require_value(), "time limit");
        } else if (argument == "--threads") {
            options.threads = parse_int(require_value(), "thread count");
        } else if (argument == "--seed") {
            options.seed = parse_u64(require_value(), "seed");
        } else if (argument == "--start") {
            options.start_path = require_value();
        } else if (argument == "--output") {
            options.output_path = require_value();
        } else if (argument == "--help") {
            std::cout
                << "usage: search_code [options]\n"
                << "  --centers N   number of centers, default 16\n"
                << "  --seconds N   wall-clock limit, default 60\n"
                << "  --threads N   worker count, default hardware count\n"
                << "  --seed N      base random seed\n"
                << "  --start PATH  optional larger reference code\n"
                << "  --output PATH best code destination\n";
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }

    if (options.centers <= 0 ||
        options.centers >= ternary_cover::kSpaceSize) {
        throw std::invalid_argument("center count is outside the valid range");
    }
    if (options.seconds <= 0) {
        throw std::invalid_argument("time limit must be positive");
    }
    if (options.threads <= 0) {
        options.threads = static_cast<int>(
            std::max(1u, std::thread::hardware_concurrency()));
    }
    return options;
}

struct SearchState {
    std::vector<int> centers;
    std::array<int, ternary_cover::kSpaceSize> position{};
    std::array<std::uint8_t, ternary_cover::kSpaceSize> multiplicity{};
    std::array<std::uint32_t, ternary_cover::kSpaceSize> weights{};
    std::array<int, ternary_cover::kSpaceSize> tabu_until{};
    int holes = ternary_cover::kSpaceSize;
    int singles = 0;

    explicit SearchState(int center_count) : centers(center_count, 0) {
        position.fill(-1);
        weights.fill(1);
        tabu_until.fill(0);
    }
};

void add_center(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    int center,
    int slot) {
    state.centers[static_cast<std::size_t>(slot)] = center;
    state.position[static_cast<std::size_t>(center)] = slot;
    for (int point :
         geometry.balls[static_cast<std::size_t>(center)]) {
        std::uint8_t& value =
            state.multiplicity[static_cast<std::size_t>(point)];
        if (value == 0) {
            --state.holes;
            ++state.singles;
        } else if (value == 1) {
            --state.singles;
        }
        ++value;
    }
}

void remove_center(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    int slot) {
    const int center = state.centers[static_cast<std::size_t>(slot)];
    state.position[static_cast<std::size_t>(center)] = -1;
    for (int point :
         geometry.balls[static_cast<std::size_t>(center)]) {
        std::uint8_t& value =
            state.multiplicity[static_cast<std::size_t>(point)];
        if (value == 1) {
            ++state.holes;
            --state.singles;
        } else if (value == 2) {
            ++state.singles;
        }
        --value;
    }
}

std::int64_t point_cost(std::uint8_t multiplicity, std::uint32_t weight) {
    if (multiplicity == 0) {
        return static_cast<std::int64_t>(weight) * 10000;
    }
    if (multiplicity == 1) {
        return 1;
    }
    return 0;
}

std::int64_t swap_delta(
    const ternary_cover::Geometry& geometry,
    const SearchState& state,
    int old_center,
    int new_center) {
    const auto& old_mask =
        geometry.masks[static_cast<std::size_t>(old_center)];
    const auto& new_mask =
        geometry.masks[static_cast<std::size_t>(new_center)];
    const auto changed = old_mask | new_mask;

    std::int64_t delta = 0;
    for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
        if (!changed.test(static_cast<std::size_t>(point))) {
            continue;
        }
        const std::uint8_t before =
            state.multiplicity[static_cast<std::size_t>(point)];
        const int after_int =
            static_cast<int>(before) -
            static_cast<int>(old_mask.test(static_cast<std::size_t>(point))) +
            static_cast<int>(new_mask.test(static_cast<std::size_t>(point)));
        const auto after = static_cast<std::uint8_t>(after_int);
        const std::uint32_t weight =
            state.weights[static_cast<std::size_t>(point)];
        delta += point_cost(after, weight) - point_cost(before, weight);
    }
    return delta;
}

void perform_swap(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    int slot,
    int new_center) {
    remove_center(geometry, state, slot);
    add_center(geometry, state, new_center, slot);
}

void initialize_from_reference(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    const std::vector<int>& reference,
    std::mt19937_64& rng) {
    std::vector<int> pool = reference;
    std::shuffle(pool.begin(), pool.end(), rng);

    int slot = 0;
    for (int center : pool) {
        if (slot == static_cast<int>(state.centers.size())) {
            break;
        }
        if (state.position[static_cast<std::size_t>(center)] == -1) {
            add_center(geometry, state, center, slot++);
        }
    }

    std::uniform_int_distribution<int> word_distribution(
        0, ternary_cover::kSpaceSize - 1);
    while (slot < static_cast<int>(state.centers.size())) {
        const int center = word_distribution(rng);
        if (state.position[static_cast<std::size_t>(center)] == -1) {
            add_center(geometry, state, center, slot++);
        }
    }
}

void initialize_greedy(
    const ternary_cover::Geometry& geometry,
    SearchState& state,
    std::mt19937_64& rng) {
    std::uniform_int_distribution<int> word_distribution(
        0, ternary_cover::kSpaceSize - 1);
    add_center(geometry, state, word_distribution(rng), 0);

    for (int slot = 1; slot < static_cast<int>(state.centers.size()); ++slot) {
        int best_gain = -1;
        std::vector<int> best_centers;
        for (int center = 0; center < ternary_cover::kSpaceSize; ++center) {
            if (state.position[static_cast<std::size_t>(center)] != -1) {
                continue;
            }
            int gain = 0;
            for (int point :
                 geometry.balls[static_cast<std::size_t>(center)]) {
                gain += state.multiplicity[static_cast<std::size_t>(point)] == 0;
            }
            if (gain > best_gain) {
                best_gain = gain;
                best_centers.assign(1, center);
            } else if (gain == best_gain) {
                best_centers.push_back(center);
            }
        }
        std::uniform_int_distribution<std::size_t> choice(
            0, best_centers.size() - 1);
        add_center(geometry, state, best_centers[choice(rng)], slot);
    }
}

int choose_hole(const SearchState& state, std::mt19937_64& rng) {
    std::vector<int> holes;
    std::uint64_t total_weight = 0;
    for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
        if (state.multiplicity[static_cast<std::size_t>(point)] == 0) {
            holes.push_back(point);
            total_weight += state.weights[static_cast<std::size_t>(point)];
        }
    }
    if (holes.empty()) {
        return -1;
    }
    std::uniform_int_distribution<std::uint64_t> draw(1, total_weight);
    std::uint64_t target = draw(rng);
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

struct SharedBest {
    std::atomic<bool> found{false};
    std::atomic<int> holes{ternary_cover::kSpaceSize};
    std::atomic<std::uint64_t> steps{0};
    std::mutex mutex;
    std::vector<int> centers;
};

void report_best(
    const Options& options,
    const SearchState& state,
    SharedBest& shared) {
    int observed = shared.holes.load(std::memory_order_relaxed);
    while (state.holes < observed &&
           !shared.holes.compare_exchange_weak(
               observed, state.holes, std::memory_order_relaxed)) {
    }
    if (state.holes > shared.holes.load(std::memory_order_relaxed)) {
        return;
    }

    std::lock_guard<std::mutex> lock(shared.mutex);
    if (shared.centers.empty() ||
        state.holes <= shared.holes.load(std::memory_order_relaxed)) {
        shared.centers = state.centers;
        std::sort(shared.centers.begin(), shared.centers.end());
        const std::filesystem::path output(options.output_path);
        if (output.has_parent_path()) {
            std::filesystem::create_directories(output.parent_path());
        }
        ternary_cover::write_code(options.output_path, shared.centers);
    }
}

void worker(
    int worker_id,
    const Options& options,
    const ternary_cover::Geometry& geometry,
    const std::vector<int>& reference,
    std::chrono::steady_clock::time_point deadline,
    SharedBest& shared) {
    std::seed_seq seed_sequence{
        static_cast<std::uint32_t>(options.seed),
        static_cast<std::uint32_t>(options.seed >> 32),
        static_cast<std::uint32_t>(worker_id),
        0x6b335f62u};
    std::mt19937_64 rng(seed_sequence);

    std::uint64_t local_steps = 0;
    int restart = 0;
    while (!shared.found.load(std::memory_order_relaxed) &&
           std::chrono::steady_clock::now() < deadline) {
        SearchState state(options.centers);
        if (!reference.empty() && (restart % 3 != 2)) {
            initialize_from_reference(geometry, state, reference, rng);
        } else {
            initialize_greedy(geometry, state, rng);
        }
        report_best(options, state, shared);

        int stagnation = 0;
        const int restart_limit = 20000 + 1000 * (worker_id % 7);
        for (int iteration = 1;
             iteration <= restart_limit &&
             !shared.found.load(std::memory_order_relaxed) &&
             std::chrono::steady_clock::now() < deadline;
             ++iteration) {
            if (state.holes == 0) {
                report_best(options, state, shared);
                shared.found.store(true, std::memory_order_relaxed);
                break;
            }

            const int hole = choose_hole(state, rng);
            std::int64_t best_delta =
                std::numeric_limits<std::int64_t>::max();
            std::vector<std::pair<int, int>> best_moves;

            for (int slot = 0;
                 slot < static_cast<int>(state.centers.size());
                 ++slot) {
                const int old_center =
                    state.centers[static_cast<std::size_t>(slot)];
                for (int new_center :
                     geometry.balls[static_cast<std::size_t>(hole)]) {
                    if (new_center == old_center ||
                        state.position[static_cast<std::size_t>(new_center)] !=
                            -1) {
                        continue;
                    }
                    const bool tabu =
                        state.tabu_until[static_cast<std::size_t>(new_center)] >
                        iteration;
                    const std::int64_t delta =
                        swap_delta(geometry, state, old_center, new_center);
                    const bool aspiration =
                        state.holes == shared.holes.load(
                            std::memory_order_relaxed) &&
                        delta < 0;
                    if (tabu && !aspiration) {
                        continue;
                    }
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_moves.assign(1, {slot, new_center});
                    } else if (delta == best_delta) {
                        best_moves.emplace_back(slot, new_center);
                    }
                }
            }

            if (best_moves.empty()) {
                break;
            }

            std::uniform_int_distribution<std::size_t> choose_move(
                0, best_moves.size() - 1);
            const auto [slot, new_center] =
                best_moves[choose_move(rng)];
            const int removed =
                state.centers[static_cast<std::size_t>(slot)];
            perform_swap(geometry, state, slot, new_center);
            std::uniform_int_distribution<int> tenure(7, 19);
            state.tabu_until[static_cast<std::size_t>(removed)] =
                iteration + tenure(rng);

            ++local_steps;
            if (state.holes <
                shared.holes.load(std::memory_order_relaxed)) {
                report_best(options, state, shared);
                stagnation = 0;
            } else {
                ++stagnation;
            }

            if (stagnation >= 80) {
                for (int point = 0;
                     point < ternary_cover::kSpaceSize;
                     ++point) {
                    if (state.multiplicity[static_cast<std::size_t>(point)] ==
                        0) {
                        ++state.weights[static_cast<std::size_t>(point)];
                    }
                }
                stagnation = 0;
            }

            if (iteration % 2500 == 0) {
                std::uniform_int_distribution<int> slot_distribution(
                    0, options.centers - 1);
                std::uniform_int_distribution<int> word_distribution(
                    0, ternary_cover::kSpaceSize - 1);
                for (int perturb = 0; perturb < 2; ++perturb) {
                    const int random_slot = slot_distribution(rng);
                    int random_center = word_distribution(rng);
                    while (state.position[
                               static_cast<std::size_t>(random_center)] != -1) {
                        random_center = word_distribution(rng);
                    }
                    perform_swap(
                        geometry, state, random_slot, random_center);
                }
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
        std::vector<int> reference;
        if (!options.start_path.empty()) {
            reference = ternary_cover::read_code(options.start_path);
        }

        SharedBest shared;
        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::seconds(options.seconds);
        std::vector<std::thread> workers;
        workers.reserve(static_cast<std::size_t>(options.threads));
        for (int worker_id = 0; worker_id < options.threads; ++worker_id) {
            workers.emplace_back(
                worker,
                worker_id,
                std::cref(options),
                std::cref(geometry),
                std::cref(reference),
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
        std::cout << "best code: " << options.output_path << '\n';
        if (shared.found.load(std::memory_order_relaxed)) {
            std::cout << "cover found: yes\n";
            return 0;
        }
        std::cout << "cover found: no\n";
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
