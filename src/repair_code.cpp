#include "ternary_cover.hpp"

#include <algorithm>
#include <array>
#include <chrono>
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <utility>
#include <vector>

namespace {

struct Options {
    std::string input_path;
    std::string output_path = "search-results/repaired_16_code.txt";
    int remove_count = 3;
    int seconds = 300;
    std::uint64_t seed = 1;
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
    if (argc < 2) {
        throw std::invalid_argument(
            "usage: repair_code CODE_FILE [options]");
    }
    Options options;
    options.input_path = argv[1];
    for (int i = 2; i < argc; ++i) {
        const std::string argument = argv[i];
        auto require_value = [&]() -> const char* {
            if (i + 1 >= argc) {
                throw std::invalid_argument(
                    "missing value after " + argument);
            }
            return argv[++i];
        };
        if (argument == "--remove") {
            options.remove_count =
                parse_int(require_value(), "removal count");
        } else if (argument == "--seconds") {
            options.seconds = parse_int(require_value(), "time limit");
        } else if (argument == "--seed") {
            options.seed = parse_u64(require_value(), "seed");
        } else if (argument == "--output") {
            options.output_path = require_value();
        } else if (argument == "--help") {
            std::cout
                << "usage: repair_code CODE_FILE [options]\n"
                << "  --remove N    replace N centers, default 3\n"
                << "  --seconds N   wall-clock limit, default 300\n"
                << "  --seed N      subset-order seed\n"
                << "  --output PATH repaired code destination\n";
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }
    if (options.remove_count <= 0 || options.remove_count > 8) {
        throw std::invalid_argument("removal count must be in 1..8");
    }
    if (options.seconds <= 0) {
        throw std::invalid_argument("time limit must be positive");
    }
    return options;
}

std::vector<std::vector<int>> combinations(int n, int choose) {
    std::vector<std::vector<int>> result;
    std::vector<int> current;
    const auto visit = [&](auto&& self, int next) -> void {
        if (static_cast<int>(current.size()) == choose) {
            result.push_back(current);
            return;
        }
        const int needed = choose - static_cast<int>(current.size());
        for (int value = next; value <= n - needed; ++value) {
            current.push_back(value);
            self(self, value + 1);
            current.pop_back();
        }
    };
    visit(visit, 0);
    return result;
}

struct RepairSearch {
    const ternary_cover::Geometry& geometry;
    std::chrono::steady_clock::time_point deadline;
    std::uint64_t nodes = 0;
    bool timed_out = false;

    bool packing_exceeds(
        const ternary_cover::Mask& residual,
        int slots) const {
        std::vector<int> points;
        points.reserve(residual.count());
        for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
            if (residual.test(static_cast<std::size_t>(point))) {
                points.push_back(point);
            }
        }
        const int trials = std::min<int>(12, points.size());
        for (int trial = 0; trial < trials; ++trial) {
            std::vector<int> packing;
            for (std::size_t offset = 0; offset < points.size(); ++offset) {
                const int point = points[
                    (offset + static_cast<std::size_t>(trial)) %
                    points.size()];
                bool compatible = true;
                for (int chosen : packing) {
                    if (ternary_cover::hamming_distance(point, chosen) <= 4) {
                        compatible = false;
                        break;
                    }
                }
                if (compatible) {
                    packing.push_back(point);
                    if (static_cast<int>(packing.size()) > slots) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    bool gain_bounds_fail(
        const ternary_cover::Mask& residual,
        int slots,
        std::vector<std::pair<int, int>>& gains) const {
        gains.clear();
        gains.reserve(ternary_cover::kSpaceSize);
        for (int center = 0; center < ternary_cover::kSpaceSize; ++center) {
            const int gain = static_cast<int>(
                (geometry.masks[static_cast<std::size_t>(center)] &
                 residual).count());
            if (gain > 0) {
                gains.emplace_back(gain, center);
            }
        }
        std::sort(gains.begin(), gains.end(), std::greater<>());
        if (gains.empty()) {
            return true;
        }
        const int residual_size = static_cast<int>(residual.count());
        if ((residual_size + gains.front().first - 1) /
                gains.front().first >
            slots) {
            return true;
        }
        int optimistic = 0;
        for (int i = 0;
             i < slots && i < static_cast<int>(gains.size());
             ++i) {
            optimistic += gains[static_cast<std::size_t>(i)].first;
        }
        return optimistic < residual_size;
    }

    int choose_target(
        const ternary_cover::Mask& residual,
        const std::vector<std::pair<int, int>>& gains) const {
        std::array<int, ternary_cover::kSpaceSize> gain_by_center{};
        for (const auto [gain, center] : gains) {
            gain_by_center[static_cast<std::size_t>(center)] = gain;
        }

        int best_point = -1;
        std::int64_t best_score =
            std::numeric_limits<std::int64_t>::max();
        for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
            if (!residual.test(static_cast<std::size_t>(point))) {
                continue;
            }
            std::int64_t score = 0;
            for (int center :
                 geometry.balls[static_cast<std::size_t>(point)]) {
                const int gain =
                    gain_by_center[static_cast<std::size_t>(center)];
                score += static_cast<std::int64_t>(gain) * gain;
            }
            if (score < best_score) {
                best_score = score;
                best_point = point;
            }
        }
        return best_point;
    }

    bool solve(
        const ternary_cover::Mask& residual,
        int slots,
        std::vector<int>& additions) {
        ++nodes;
        if ((nodes & 0x3ffu) == 0 &&
            std::chrono::steady_clock::now() >= deadline) {
            timed_out = true;
            return false;
        }
        if (residual.none()) {
            return true;
        }
        if (slots == 0 || packing_exceeds(residual, slots)) {
            return false;
        }

        if (slots == 1) {
            ternary_cover::Mask candidates;
            candidates.set();
            for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
                if (residual.test(static_cast<std::size_t>(point))) {
                    candidates &=
                        geometry.masks[static_cast<std::size_t>(point)];
                }
            }
            for (int center = 0; center < ternary_cover::kSpaceSize; ++center) {
                if (candidates.test(static_cast<std::size_t>(center))) {
                    additions.push_back(center);
                    return true;
                }
            }
            return false;
        }

        std::vector<std::pair<int, int>> gains;
        if (gain_bounds_fail(residual, slots, gains)) {
            return false;
        }
        const int target = choose_target(residual, gains);
        if (target < 0) {
            return false;
        }

        std::array<int, ternary_cover::kSpaceSize> gain_by_center{};
        for (const auto [gain, center] : gains) {
            gain_by_center[static_cast<std::size_t>(center)] = gain;
        }
        std::vector<std::pair<int, int>> branches;
        branches.reserve(ternary_cover::kBallSize);
        for (int center :
             geometry.balls[static_cast<std::size_t>(target)]) {
            const int gain =
                gain_by_center[static_cast<std::size_t>(center)];
            if (gain > 0) {
                branches.emplace_back(gain, center);
            }
        }
        std::sort(branches.begin(), branches.end(), std::greater<>());

        std::vector<ternary_cover::Mask> seen_residuals;
        seen_residuals.reserve(branches.size());
        for (const auto [gain, center] : branches) {
            static_cast<void>(gain);
            ternary_cover::Mask next =
                residual &
                ~geometry.masks[static_cast<std::size_t>(center)];
            if (std::find(seen_residuals.begin(), seen_residuals.end(), next) !=
                seen_residuals.end()) {
                continue;
            }
            seen_residuals.push_back(next);
            additions.push_back(center);
            if (solve(next, slots - 1, additions)) {
                return true;
            }
            additions.pop_back();
            if (timed_out) {
                return false;
            }
        }
        return false;
    }
};

ternary_cover::Mask residual_for_fixed(
    const ternary_cover::Geometry& geometry,
    const std::vector<int>& fixed) {
    ternary_cover::Mask residual;
    residual.set();
    for (int center : fixed) {
        residual &= ~geometry.masks[static_cast<std::size_t>(center)];
    }
    return residual;
}

std::vector<int> build_fixed(
    const std::vector<int>& code,
    const std::vector<int>& removed_slots) {
    std::vector<bool> removed(code.size(), false);
    for (int slot : removed_slots) {
        removed[static_cast<std::size_t>(slot)] = true;
    }
    std::vector<int> fixed;
    for (std::size_t slot = 0; slot < code.size(); ++slot) {
        if (!removed[slot]) {
            fixed.push_back(code[slot]);
        }
    }
    return fixed;
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const ternary_cover::Geometry geometry;
        const std::vector<int> code =
            ternary_cover::read_code(options.input_path);
        if (options.remove_count >= static_cast<int>(code.size())) {
            throw std::invalid_argument(
                "removal count must be smaller than the code size");
        }

        std::vector<std::vector<int>> removal_sets =
            combinations(static_cast<int>(code.size()), options.remove_count);
        std::mt19937_64 rng(options.seed);
        std::shuffle(removal_sets.begin(), removal_sets.end(), rng);
        std::stable_sort(
            removal_sets.begin(),
            removal_sets.end(),
            [&](const std::vector<int>& lhs, const std::vector<int>& rhs) {
                const auto lhs_fixed = build_fixed(code, lhs);
                const auto rhs_fixed = build_fixed(code, rhs);
                return residual_for_fixed(geometry, lhs_fixed).count() <
                       residual_for_fixed(geometry, rhs_fixed).count();
            });

        const auto deadline =
            std::chrono::steady_clock::now() +
            std::chrono::seconds(options.seconds);
        std::uint64_t total_nodes = 0;
        std::size_t attempted = 0;
        for (const std::vector<int>& removed_slots : removal_sets) {
            if (std::chrono::steady_clock::now() >= deadline) {
                break;
            }
            ++attempted;
            std::vector<int> fixed = build_fixed(code, removed_slots);
            const ternary_cover::Mask residual =
                residual_for_fixed(geometry, fixed);

            RepairSearch search{geometry, deadline};
            std::vector<int> additions;
            if (search.solve(residual, options.remove_count, additions)) {
                std::vector<int> repaired = fixed;
                for (int center : additions) {
                    if (std::find(repaired.begin(), repaired.end(), center) ==
                        repaired.end()) {
                        repaired.push_back(center);
                    }
                }
                for (int center = 0;
                     repaired.size() < code.size() &&
                     center < ternary_cover::kSpaceSize;
                     ++center) {
                    if (std::find(repaired.begin(), repaired.end(), center) ==
                        repaired.end()) {
                        repaired.push_back(center);
                    }
                }
                const auto verification =
                    ternary_cover::verify_code(geometry, repaired);
                if (!verification.distinct || verification.holes != 0) {
                    throw std::logic_error(
                        "internal repair result failed verification");
                }
                std::sort(repaired.begin(), repaired.end());
                const std::filesystem::path output(options.output_path);
                if (output.has_parent_path()) {
                    std::filesystem::create_directories(
                        output.parent_path());
                }
                ternary_cover::write_code(options.output_path, repaired);
                std::cout << "repair found: yes\n";
                std::cout << "attempted subsets: " << attempted << '\n';
                std::cout << "nodes: " << total_nodes + search.nodes << '\n';
                std::cout << "output: " << options.output_path << '\n';
                return 0;
            }
            total_nodes += search.nodes;
            if (search.timed_out) {
                break;
            }
        }

        std::cout << "repair found: no\n";
        std::cout << "attempted subsets: " << attempted << '/'
                  << removal_sets.size() << '\n';
        std::cout << "nodes: " << total_nodes << '\n';
        return 1;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}

