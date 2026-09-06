#include "ternary_cover.hpp"

#include <algorithm>
#include <array>
#include <iostream>
#include <map>
#include <numeric>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

struct Options {
    int centers = 16;
    bool exact = true;
    bool fix_zero = false;
    int maximum_weight = ternary_cover::kLength;
    int anchor_weight = -1;
    int third_orbit = -1;
    bool list_third_orbits = false;
    bool branch_manifest_json = false;
    int fourth_orbit = -1;
    bool list_fourth_orbits = false;
    int fifth_orbit = -1;
    bool list_fifth_orbits = false;
    std::vector<int> orbit_path;
    bool list_next_orbits = false;
    bool structural_constraints = true;
    bool projection_cuts = false;
    bool four_projection_cuts = false;
    bool five_projection_cuts = false;
    bool antipodal_cuts = false;
    bool radial_sphere_cuts = false;
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
        } else if (argument == "--at-most") {
            options.exact = false;
        } else if (argument == "--fix-zero") {
            options.fix_zero = true;
        } else if (argument == "--maximum-weight") {
            options.maximum_weight =
                parse_int(require_value(), "maximum weight");
        } else if (argument == "--anchor-weight") {
            options.anchor_weight =
                parse_int(require_value(), "anchor weight");
        } else if (argument == "--third-orbit") {
            options.third_orbit =
                parse_int(require_value(), "third-center orbit");
        } else if (argument == "--list-third-orbits") {
            options.list_third_orbits = true;
        } else if (argument == "--branch-manifest-json") {
            options.branch_manifest_json = true;
        } else if (argument == "--fourth-orbit") {
            options.fourth_orbit =
                parse_int(require_value(), "fourth-center orbit");
        } else if (argument == "--list-fourth-orbits") {
            options.list_fourth_orbits = true;
        } else if (argument == "--fifth-orbit") {
            options.fifth_orbit =
                parse_int(require_value(), "fifth-center orbit");
        } else if (argument == "--list-fifth-orbits") {
            options.list_fifth_orbits = true;
        } else if (argument == "--orbit-path") {
            const std::string text = require_value();
            std::size_t begin = 0;
            while (begin < text.size()) {
                const std::size_t comma = text.find(',', begin);
                const std::size_t end =
                    comma == std::string::npos ? text.size() : comma;
                if (end == begin) {
                    throw std::invalid_argument("empty orbit-path component");
                }
                options.orbit_path.push_back(
                    parse_int(
                        text.substr(begin, end - begin).c_str(),
                        "orbit-path component"));
                begin = end + 1;
            }
        } else if (argument == "--list-next-orbits") {
            options.list_next_orbits = true;
        } else if (argument == "--no-structural") {
            options.structural_constraints = false;
        } else if (argument == "--projection-cuts") {
            options.projection_cuts = true;
        } else if (argument == "--four-projection-cuts") {
            options.four_projection_cuts = true;
        } else if (argument == "--five-projection-cuts") {
            options.five_projection_cuts = true;
        } else if (argument == "--antipodal-cuts") {
            options.antipodal_cuts = true;
        } else if (argument == "--radial-sphere-cuts") {
            options.radial_sphere_cuts = true;
        } else if (argument == "--help") {
            std::cout
                << "usage: generate_cnf [options]\n"
                << "  --centers N          center count, default 16\n"
                << "  --at-most            allow fewer than N centers\n"
                << "  --fix-zero           require center 000000\n"
                << "  --maximum-weight D   forbid centers above weight D\n"
                << "  --anchor-weight D    require 11..100..0 of weight D\n"
                << "  --third-orbit I      fix earliest occupied third orbit\n"
                << "  --list-third-orbits  print orbit indices and exit\n"
                << "  --branch-manifest-json print fixed and forbidden centers\n"
                << "  --fourth-orbit I     fix earliest occupied fourth orbit\n"
                << "  --list-fourth-orbits print fourth orbits and exit\n"
                << "  --fifth-orbit I      fix earliest occupied fifth orbit\n"
                << "  --list-fifth-orbits  print fifth orbits and exit\n"
                << "  --orbit-path A,B,... arbitrary-depth orbit branch\n"
                << "  --list-next-orbits   print next orbits after path\n"
                << "  --no-structural      omit proven symbol-count cuts\n"
                << "  --projection-cuts    add two-coordinate capacity cuts\n"
                << "  --four-projection-cuts add four-coordinate cuts\n"
                << "  --five-projection-cuts add five-coordinate cuts\n"
                << "  --antipodal-cuts     add cuts at symmetry-fixed centers\n"
                << "  --radial-sphere-cuts add distance-1 and distance-2 cuts\n";
            std::exit(0);
        } else {
            throw std::invalid_argument("unknown option: " + argument);
        }
    }

    if (options.centers <= 0 ||
        options.centers >= ternary_cover::kSpaceSize) {
        throw std::invalid_argument("center bound is outside the valid range");
    }
    if (options.maximum_weight < 0 ||
        options.maximum_weight > ternary_cover::kLength) {
        throw std::invalid_argument("maximum weight is outside 0..6");
    }
    if (options.anchor_weight > ternary_cover::kLength) {
        throw std::invalid_argument("anchor weight is outside 0..6");
    }
    if (options.anchor_weight >= 0) {
        options.fix_zero = true;
        options.maximum_weight = options.anchor_weight;
    }
    if ((options.third_orbit >= 0 || options.list_third_orbits) &&
        options.anchor_weight < 0) {
        throw std::invalid_argument(
            "third-center orbits require --anchor-weight");
    }
    if (options.branch_manifest_json && options.third_orbit < 0) {
        throw std::invalid_argument(
            "branch manifest requires --third-orbit");
    }
    if ((options.fourth_orbit >= 0 || options.list_fourth_orbits) &&
        options.third_orbit < 0) {
        throw std::invalid_argument(
            "fourth-center orbits require --third-orbit");
    }
    if ((options.fifth_orbit >= 0 || options.list_fifth_orbits) &&
        options.fourth_orbit < 0) {
        throw std::invalid_argument(
            "fifth-center orbits require --fourth-orbit");
    }
    if ((!options.orbit_path.empty() || options.list_next_orbits) &&
        options.anchor_weight < 0) {
        throw std::invalid_argument(
            "generic orbit paths require --anchor-weight");
    }
    if (!options.orbit_path.empty() &&
        (options.third_orbit >= 0 ||
         options.fourth_orbit >= 0 ||
         options.fifth_orbit >= 0)) {
        throw std::invalid_argument(
            "--orbit-path cannot be combined with fixed-level orbit options");
    }
    const bool uses_orbit_branching =
        options.third_orbit >= 0 ||
        options.list_third_orbits ||
        options.fourth_orbit >= 0 ||
        options.list_fourth_orbits ||
        options.fifth_orbit >= 0 ||
        options.list_fifth_orbits ||
        !options.orbit_path.empty() ||
        options.list_next_orbits;
    if (uses_orbit_branching && !options.exact) {
        throw std::invalid_argument(
            "orbit branching requires exact cardinality");
    }
    if (uses_orbit_branching && options.centers != 16) {
        throw std::invalid_argument(
            "orbit branching is specialized to exactly 16 centers");
    }
    if (options.anchor_weight >= 0 && options.centers < 2) {
        throw std::invalid_argument(
            "the normalized anchor requires at least two centers");
    }
    if (options.orbit_path.size() >
        static_cast<std::size_t>(options.centers - 2)) {
        throw std::invalid_argument(
            "orbit path fixes more centers than the exact cardinality");
    }
    if (options.centers != 16 &&
        (options.structural_constraints ||
         options.projection_cuts ||
         options.four_projection_cuts ||
         options.five_projection_cuts ||
         options.antipodal_cuts ||
         options.radial_sphere_cuts)) {
        throw std::invalid_argument(
            "structural and projection cuts are specialized to 16 centers");
    }
    return options;
}

struct Cnf {
    int variables = ternary_cover::kSpaceSize;
    std::vector<std::vector<int>> clauses;

    int fresh_variable() {
        return ++variables;
    }

    void add(std::vector<int> clause) {
        clauses.push_back(std::move(clause));
    }
};

int selection_variable(int center) {
    return center + 1;
}

int anchor_word(int weight) {
    ternary_cover::Digits digits{};
    for (int i = 0; i < weight; ++i) {
        digits[static_cast<std::size_t>(i)] = 1;
    }
    return ternary_cover::encode(digits);
}

int third_candidate_max_weight(int anchor_weight) {
    return std::min(anchor_weight, 4);
}

using OrbitKey = std::tuple<int, int, int, int>;

OrbitKey third_orbit_key(int word, int anchor_weight) {
    const ternary_cover::Digits digits = ternary_cover::decode(word);
    std::array<int, ternary_cover::kAlphabet> support_counts{};
    int outside_nonzero = 0;
    for (int coordinate = 0; coordinate < ternary_cover::kLength;
         ++coordinate) {
        const int digit =
            digits[static_cast<std::size_t>(coordinate)];
        if (coordinate < anchor_weight) {
            ++support_counts[static_cast<std::size_t>(digit)];
        } else {
            outside_nonzero += digit != 0;
        }
    }
    return {
        support_counts[0],
        support_counts[1],
        support_counts[2],
        outside_nonzero};
}

struct ThirdOrbit {
    OrbitKey key{};
    int representative = -1;
    std::vector<int> members;
};

struct Automorphism {
    std::array<int, ternary_cover::kLength> source{};
    std::array<bool, ternary_cover::kLength> flip_nonzero{};

    int apply(int word) const {
        const auto input = ternary_cover::decode(word);
        ternary_cover::Digits output{};
        for (int coordinate = 0;
             coordinate < ternary_cover::kLength;
             ++coordinate) {
            int digit = input[static_cast<std::size_t>(
                source[static_cast<std::size_t>(coordinate)])];
            if (flip_nonzero[static_cast<std::size_t>(coordinate)] &&
                digit != 0) {
                digit = 3 - digit;
            }
            output[static_cast<std::size_t>(coordinate)] =
                static_cast<std::uint8_t>(digit);
        }
        return ternary_cover::encode(output);
    }
};

std::vector<Automorphism> stabilizer(
    int anchor_weight,
    const std::vector<int>& fixed_words) {
    std::vector<int> support(static_cast<std::size_t>(anchor_weight));
    std::iota(support.begin(), support.end(), 0);
    std::vector<int> outside(
        static_cast<std::size_t>(
            ternary_cover::kLength - anchor_weight));
    std::iota(
        outside.begin(),
        outside.end(),
        anchor_weight);

    std::vector<Automorphism> result;
    do {
        std::vector<int> outside_permutation = outside;
        do {
            const int outside_size =
                ternary_cover::kLength - anchor_weight;
            const int flip_count = 1 << outside_size;
            for (int mask = 0; mask < flip_count; ++mask) {
                Automorphism automorphism;
                for (int coordinate = 0;
                     coordinate < anchor_weight;
                     ++coordinate) {
                    automorphism.source[
                        static_cast<std::size_t>(coordinate)] =
                        support[static_cast<std::size_t>(coordinate)];
                }
                for (int offset = 0; offset < outside_size; ++offset) {
                    const int coordinate = anchor_weight + offset;
                    automorphism.source[
                        static_cast<std::size_t>(coordinate)] =
                        outside_permutation[static_cast<std::size_t>(offset)];
                    automorphism.flip_nonzero[
                        static_cast<std::size_t>(coordinate)] =
                        ((mask >> offset) & 1) != 0;
                }

                bool fixes_all = true;
                for (int fixed : fixed_words) {
                    if (automorphism.apply(fixed) != fixed) {
                        fixes_all = false;
                        break;
                    }
                }
                if (fixes_all) {
                    result.push_back(automorphism);
                }
            }
        } while (std::next_permutation(
            outside_permutation.begin(),
            outside_permutation.end()));
    } while (std::next_permutation(support.begin(), support.end()));
    return result;
}

struct CenterOrbit {
    int representative = -1;
    std::vector<int> members;
};

std::vector<CenterOrbit> center_orbits(
    int anchor_weight,
    const std::vector<int>& fixed_words,
    const std::vector<int>& forbidden_words = {},
    int candidate_max_weight = -1) {
    const int maximum_candidate_weight =
        candidate_max_weight < 0
        ? anchor_weight
        : std::min(anchor_weight, candidate_max_weight);
    const auto group = stabilizer(anchor_weight, fixed_words);
    std::array<bool, ternary_cover::kSpaceSize> excluded{};
    for (int forbidden : forbidden_words) {
        excluded[static_cast<std::size_t>(forbidden)] = true;
    }
    for (int fixed : fixed_words) {
        excluded[static_cast<std::size_t>(fixed)] = true;
    }
    std::array<bool, ternary_cover::kSpaceSize> visited{};
    std::vector<CenterOrbit> result;

    for (int word = 0; word < ternary_cover::kSpaceSize; ++word) {
        if (visited[static_cast<std::size_t>(word)] ||
            excluded[static_cast<std::size_t>(word)] ||
            ternary_cover::hamming_weight(word) >
                maximum_candidate_weight) {
            continue;
        }
        std::vector<int> members;
        members.reserve(group.size());
        for (const Automorphism& automorphism : group) {
            members.push_back(automorphism.apply(word));
        }
        std::sort(members.begin(), members.end());
        members.erase(
            std::unique(members.begin(), members.end()),
            members.end());
        for (int member : members) {
            visited[static_cast<std::size_t>(member)] = true;
        }
        result.push_back({members.front(), std::move(members)});
    }
    std::sort(
        result.begin(),
        result.end(),
        [](const CenterOrbit& lhs, const CenterOrbit& rhs) {
            return lhs.representative < rhs.representative;
        });

    std::size_t expected = 0;
    std::size_t observed = 0;
    for (int word = 0; word < ternary_cover::kSpaceSize; ++word) {
        if (!excluded[static_cast<std::size_t>(word)] &&
            ternary_cover::hamming_weight(word) <=
                maximum_candidate_weight) {
            ++expected;
            if (!visited[static_cast<std::size_t>(word)]) {
                throw std::logic_error(
                    "stabilizer orbits do not cover every eligible center");
            }
        }
    }
    for (const CenterOrbit& orbit : result) {
        observed += orbit.members.size();
    }
    if (observed != expected) {
        throw std::logic_error(
            "stabilizer orbits are not a disjoint partition");
    }
    return result;
}

std::vector<ThirdOrbit> third_orbits(int anchor_weight) {
    const int anchor = anchor_word(anchor_weight);
    const int candidate_max_weight =
        third_candidate_max_weight(anchor_weight);
    std::map<OrbitKey, std::vector<int>> grouped;
    for (int word = 0; word < ternary_cover::kSpaceSize; ++word) {
        if (word == 0 || word == anchor ||
            ternary_cover::hamming_weight(word) >
                candidate_max_weight) {
            continue;
        }
        grouped[third_orbit_key(word, anchor_weight)].push_back(word);
    }

    std::vector<ThirdOrbit> orbits;
    orbits.reserve(grouped.size());
    for (auto& [key, members] : grouped) {
        std::sort(members.begin(), members.end());
        orbits.push_back({key, members.front(), std::move(members)});
    }
    std::sort(
        orbits.begin(),
        orbits.end(),
        [](const ThirdOrbit& lhs, const ThirdOrbit& rhs) {
            return lhs.representative < rhs.representative;
        });
    return orbits;
}

std::vector<std::vector<int>> add_threshold_counter(
    Cnf& cnf,
    const std::vector<int>& literals,
    int threshold) {
    if (literals.empty() || threshold <= 0) {
        return {};
    }

    const int n = static_cast<int>(literals.size());
    std::vector<std::vector<int>> counter(
        static_cast<std::size_t>(n),
        std::vector<int>(static_cast<std::size_t>(threshold + 1), 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 1; j <= threshold; ++j) {
            counter[static_cast<std::size_t>(i)]
                   [static_cast<std::size_t>(j)] =
                cnf.fresh_variable();
        }
    }

    cnf.add({-literals[0], counter[0][1]});
    cnf.add({-counter[0][1], literals[0]});
    for (int j = 2; j <= threshold; ++j) {
        cnf.add({-counter[0][static_cast<std::size_t>(j)]});
    }

    for (int i = 1; i < n; ++i) {
        cnf.add({
            -literals[static_cast<std::size_t>(i)],
            counter[static_cast<std::size_t>(i)][1]});
        cnf.add({
            -counter[static_cast<std::size_t>(i - 1)][1],
            counter[static_cast<std::size_t>(i)][1]});
        cnf.add({
            -counter[static_cast<std::size_t>(i)][1],
            counter[static_cast<std::size_t>(i - 1)][1],
            literals[static_cast<std::size_t>(i)]});

        for (int j = 2; j <= threshold; ++j) {
            cnf.add({
                -counter[static_cast<std::size_t>(i - 1)]
                        [static_cast<std::size_t>(j)],
                counter[static_cast<std::size_t>(i)]
                       [static_cast<std::size_t>(j)]});
            cnf.add({
                -literals[static_cast<std::size_t>(i)],
                -counter[static_cast<std::size_t>(i - 1)]
                        [static_cast<std::size_t>(j - 1)],
                counter[static_cast<std::size_t>(i)]
                       [static_cast<std::size_t>(j)]});
            cnf.add({
                -counter[static_cast<std::size_t>(i)]
                        [static_cast<std::size_t>(j)],
                counter[static_cast<std::size_t>(i - 1)]
                       [static_cast<std::size_t>(j)],
                counter[static_cast<std::size_t>(i - 1)]
                       [static_cast<std::size_t>(j - 1)]});
            cnf.add({
                -counter[static_cast<std::size_t>(i)]
                        [static_cast<std::size_t>(j)],
                counter[static_cast<std::size_t>(i - 1)]
                       [static_cast<std::size_t>(j)],
                literals[static_cast<std::size_t>(i)]});
        }
    }
    return counter;
}

void add_between(
    Cnf& cnf,
    const std::vector<int>& literals,
    int lower,
    int upper) {
    const int n = static_cast<int>(literals.size());
    if (lower < 0 || upper < lower || upper > n) {
        throw std::invalid_argument("invalid cardinality interval");
    }
    if (n == 0) {
        if (lower > 0) {
            cnf.add({});
        }
        return;
    }

    const int threshold = std::min(n, upper + 1);
    const auto counter = add_threshold_counter(cnf, literals, threshold);
    if (lower > 0) {
        cnf.add({
            counter[static_cast<std::size_t>(n - 1)]
                   [static_cast<std::size_t>(lower)]});
    }
    if (upper < n) {
        cnf.add({
            -counter[static_cast<std::size_t>(n - 1)]
                    [static_cast<std::size_t>(upper + 1)]});
    }
}

void add_fixed_antipodal_cut(Cnf& cnf, int fixed_center) {
    std::array<std::vector<int>, 3> shells;
    shells[0].reserve(240);
    shells[1].reserve(192);
    shells[2].reserve(64);
    for (int center = 0;
         center < ternary_cover::kSpaceSize;
         ++center) {
        const int distance =
            ternary_cover::hamming_distance(fixed_center, center);
        if (distance >= 4) {
            shells[static_cast<std::size_t>(distance - 4)]
                .push_back(selection_variable(center));
        }
    }
    if (shells[0].size() != 240 ||
        shells[1].size() != 192 ||
        shells[2].size() != 64) {
        throw std::logic_error("antipodal shell has wrong size");
    }

    const auto four_counter =
        add_threshold_counter(cnf, shells[0], 16);
    const auto five_counter =
        add_threshold_counter(cnf, shells[1], 6);
    const auto six_counter =
        add_threshold_counter(cnf, shells[2], 3);
    const int four_last =
        static_cast<int>(shells[0].size()) - 1;
    const int five_last =
        static_cast<int>(shells[1].size()) - 1;
    const int six_last =
        static_cast<int>(shells[2].size()) - 1;

    const std::array<std::array<int, 6>, 3> required_four{{
        {{16, 13, 10, 7, 4, 1}},
        {{11, 8, 5, 2, 0, 0}},
        {{5, 2, 0, 0, 0, 0}},
    }};
    const std::array<int, 3> five_upper_limits{{5, 3, 1}};
    for (int six_upper = 0; six_upper <= 2; ++six_upper) {
        for (int five_upper = 0;
             five_upper <=
             five_upper_limits[static_cast<std::size_t>(six_upper)];
             ++five_upper) {
            const int required =
                required_four[static_cast<std::size_t>(six_upper)]
                             [static_cast<std::size_t>(five_upper)];
            cnf.add({
                six_counter[static_cast<std::size_t>(six_last)]
                           [static_cast<std::size_t>(six_upper + 1)],
                five_counter[static_cast<std::size_t>(five_last)]
                            [static_cast<std::size_t>(five_upper + 1)],
                four_counter[static_cast<std::size_t>(four_last)]
                            [static_cast<std::size_t>(required)]});
        }
    }
}

void add_radial_sphere_cuts(Cnf& cnf) {
    for (int point = 0;
         point < ternary_cover::kSpaceSize;
         ++point) {
        std::array<std::vector<int>, 5> shells;
        shells[0].reserve(1);
        shells[1].reserve(12);
        shells[2].reserve(60);
        shells[3].reserve(160);
        shells[4].reserve(240);
        for (int center = 0;
             center < ternary_cover::kSpaceSize;
             ++center) {
            const int distance =
                ternary_cover::hamming_distance(point, center);
            if (distance <= 4) {
                shells[static_cast<std::size_t>(distance)]
                    .push_back(selection_variable(center));
            }
        }
        if (shells[0].size() != 1 ||
            shells[1].size() != 12 ||
            shells[2].size() != 60 ||
            shells[3].size() != 160 ||
            shells[4].size() != 240) {
            throw std::logic_error("radial shell has wrong size");
        }

        std::vector<int> one_or_two = shells[1];
        one_or_two.insert(
            one_or_two.end(),
            shells[2].begin(),
            shells[2].end());
        const auto one_or_two_counter =
            add_threshold_counter(cnf, one_or_two, 3);
        const auto three_counter =
            add_threshold_counter(cnf, shells[3], 3);
        const int one_or_two_last =
            static_cast<int>(one_or_two.size()) - 1;
        const int three_last =
            static_cast<int>(shells[3].size()) - 1;

        std::vector<int> distance_one_clause = shells[0];
        distance_one_clause.insert(
            distance_one_clause.end(),
            shells[1].begin(),
            shells[1].end());
        distance_one_clause.push_back(
            one_or_two_counter[
                static_cast<std::size_t>(one_or_two_last)][3]);
        distance_one_clause.push_back(
            three_counter[
                static_cast<std::size_t>(three_last)][2]);
        cnf.add(std::move(distance_one_clause));

        std::vector<int> distance_two_clause = shells[0];
        distance_two_clause.push_back(
            one_or_two_counter[
                static_cast<std::size_t>(one_or_two_last)][3]);
        distance_two_clause.push_back(
            three_counter[
                static_cast<std::size_t>(three_last)][3]);
        distance_two_clause.insert(
            distance_two_clause.end(),
            shells[4].begin(),
            shells[4].end());
        cnf.add(std::move(distance_two_clause));
    }
}

void add_projection_cuts(Cnf& cnf) {
    for (int first = 0; first < ternary_cover::kLength; ++first) {
        for (int second = first + 1;
             second < ternary_cover::kLength;
             ++second) {
            for (int first_symbol = 0;
                 first_symbol < ternary_cover::kAlphabet;
                 ++first_symbol) {
                for (int second_symbol = 0;
                     second_symbol < ternary_cover::kAlphabet;
                     ++second_symbol) {
                    std::vector<int> cell;
                    std::vector<int> fringe;
                    cell.reserve(81);
                    fringe.reserve(324);
                    for (int center = 0;
                         center < ternary_cover::kSpaceSize;
                         ++center) {
                        const auto digits = ternary_cover::decode(center);
                        const bool matches_first =
                            digits[static_cast<std::size_t>(first)] ==
                            first_symbol;
                        const bool matches_second =
                            digits[static_cast<std::size_t>(second)] ==
                            second_symbol;
                        if (matches_first && matches_second) {
                            cell.push_back(selection_variable(center));
                        } else if (matches_first != matches_second) {
                            fringe.push_back(selection_variable(center));
                        }
                    }

                    const auto cell_counter =
                        add_threshold_counter(cnf, cell, 3);
                    const auto fringe_counter =
                        add_threshold_counter(cnf, fringe, 9);
                    const int cell_last =
                        static_cast<int>(cell.size()) - 1;
                    const int fringe_last =
                        static_cast<int>(fringe.size()) - 1;
                    const int c1 =
                        cell_counter[static_cast<std::size_t>(cell_last)][1];
                    const int c2 =
                        cell_counter[static_cast<std::size_t>(cell_last)][2];
                    const int c3 =
                        cell_counter[static_cast<std::size_t>(cell_last)][3];
                    const int u1 =
                        fringe_counter[
                            static_cast<std::size_t>(fringe_last)][1];
                    const int u5 =
                        fringe_counter[
                            static_cast<std::size_t>(fringe_last)][5];
                    const int u9 =
                        fringe_counter[
                            static_cast<std::size_t>(fringe_last)][9];

                    cnf.add({c1, u9});
                    cnf.add({c2, -c1, u5});
                    cnf.add({c3, -c2, u1});
                }
            }
        }
    }
}

void add_four_projection_cuts(Cnf& cnf) {
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
                                value % ternary_cover::kAlphabet;
                            value /= ternary_cover::kAlphabet;
                        }

                        std::array<std::vector<int>, 3> shells;
                        shells[0].reserve(9);
                        shells[1].reserve(72);
                        shells[2].reserve(216);
                        for (int center = 0;
                             center < ternary_cover::kSpaceSize;
                             ++center) {
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
                                shells[static_cast<std::size_t>(distance)]
                                    .push_back(selection_variable(center));
                            }
                        }
                        if (shells[0].size() != 9 ||
                            shells[1].size() != 72 ||
                            shells[2].size() != 216) {
                            throw std::logic_error(
                                "four-coordinate shell has wrong size");
                        }

                        const auto one_counter =
                            add_threshold_counter(cnf, shells[1], 2);
                        const auto two_counter =
                            add_threshold_counter(cnf, shells[2], 9);
                        const int one_last =
                            static_cast<int>(shells[1].size()) - 1;
                        const int two_last =
                            static_cast<int>(shells[2].size()) - 1;

                        std::vector<int> first_clause = shells[0];
                        first_clause.insert(
                            first_clause.end(),
                            shells[1].begin(),
                            shells[1].end());
                        first_clause.push_back(
                            two_counter[
                                static_cast<std::size_t>(two_last)][9]);
                        cnf.add(std::move(first_clause));

                        std::vector<int> second_clause = shells[0];
                        second_clause.push_back(
                            one_counter[
                                static_cast<std::size_t>(one_last)][2]);
                        second_clause.push_back(
                            two_counter[
                                static_cast<std::size_t>(two_last)][4]);
                        cnf.add(std::move(second_clause));
                    }
                }
            }
        }
    }
}

void add_five_projection_cuts(Cnf& cnf) {
    for (int omitted = 0; omitted < ternary_cover::kLength; ++omitted) {
        for (int pattern = 0; pattern < 243; ++pattern) {
            int value = pattern;
            std::array<int, 5> symbols{};
            for (int index = 4; index >= 0; --index) {
                symbols[static_cast<std::size_t>(index)] =
                    value % ternary_cover::kAlphabet;
                value /= ternary_cover::kAlphabet;
            }

            std::array<std::vector<int>, 3> shells;
            shells[0].reserve(3);
            shells[1].reserve(30);
            shells[2].reserve(120);
            for (int center = 0;
                 center < ternary_cover::kSpaceSize;
                 ++center) {
                const auto digits = ternary_cover::decode(center);
                int distance = 0;
                int projected_index = 0;
                for (int coordinate = 0;
                     coordinate < ternary_cover::kLength;
                     ++coordinate) {
                    if (coordinate == omitted) {
                        continue;
                    }
                    distance +=
                        digits[static_cast<std::size_t>(coordinate)] !=
                        symbols[static_cast<std::size_t>(
                            projected_index)];
                    ++projected_index;
                }
                if (distance <= 2) {
                    shells[static_cast<std::size_t>(distance)]
                        .push_back(selection_variable(center));
                }
            }
            if (shells[0].size() != 3 ||
                shells[1].size() != 30 ||
                shells[2].size() != 120) {
                throw std::logic_error(
                    "five-coordinate shell has wrong size");
            }

            const auto two_counter =
                add_threshold_counter(cnf, shells[2], 3);
            const int two_last =
                static_cast<int>(shells[2].size()) - 1;
            std::vector<int> clause = shells[0];
            clause.insert(
                clause.end(),
                shells[1].begin(),
                shells[1].end());
            clause.push_back(
                two_counter[
                    static_cast<std::size_t>(two_last)][3]);
            cnf.add(std::move(clause));
        }
    }
}

void add_far_center_cuts(Cnf& cnf) {
    for (int center = 0; center < ternary_cover::kSpaceSize; ++center) {
        std::vector<int> clause{-selection_variable(center)};
        clause.reserve(257);
        for (int other = 0; other < ternary_cover::kSpaceSize; ++other) {
            if (ternary_cover::hamming_distance(center, other) >= 5) {
                clause.push_back(selection_variable(other));
            }
        }
        cnf.add(std::move(clause));
    }
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const Options options = parse_options(argc, argv);
        const ternary_cover::Geometry geometry;
        Cnf cnf;
        std::vector<ThirdOrbit> orbits;
        std::vector<CenterOrbit> fourth_orbits;
        std::vector<CenterOrbit> fifth_orbits;
        std::vector<std::vector<CenterOrbit>> path_orbits;
        std::vector<int> path_representatives;
        std::vector<int> fourth_forbidden;
        std::vector<int> fifth_forbidden;
        if (options.anchor_weight >= 0) {
            orbits = third_orbits(options.anchor_weight);
        }
        if (options.list_third_orbits) {
            for (std::size_t index = 0; index < orbits.size(); ++index) {
                const auto [zeros, ones, twos, outside] =
                    orbits[index].key;
                std::cout
                    << index << ' '
                    << ternary_cover::format_word(
                           orbits[index].representative)
                    << " support=(" << zeros << ',' << ones << ',' << twos
                    << ") outside_nonzero=" << outside
                    << " orbit_size=" << orbits[index].members.size()
                    << '\n';
            }
            return 0;
        }
        if (options.third_orbit >= static_cast<int>(orbits.size())) {
            throw std::invalid_argument(
                "third-center orbit index is outside the branch range");
        }
        if (options.third_orbit >= 0 &&
            (options.fourth_orbit >= 0 ||
             options.list_fourth_orbits)) {
            const int anchor = anchor_word(options.anchor_weight);
            const int third =
                orbits[static_cast<std::size_t>(options.third_orbit)]
                    .representative;
            for (int orbit = 0; orbit < options.third_orbit; ++orbit) {
                const auto& members =
                    orbits[static_cast<std::size_t>(orbit)].members;
                fourth_forbidden.insert(
                    fourth_forbidden.end(),
                    members.begin(),
                    members.end());
            }
            fourth_orbits = center_orbits(
                options.anchor_weight,
                {0, anchor, third},
                fourth_forbidden);
        }
        if (options.list_fourth_orbits) {
            for (std::size_t index = 0;
                 index < fourth_orbits.size();
                 ++index) {
                std::cout
                    << index << ' '
                    << ternary_cover::format_word(
                           fourth_orbits[index].representative)
                    << " orbit_size="
                    << fourth_orbits[index].members.size()
                    << '\n';
            }
            return 0;
        }
        if (options.fourth_orbit >=
            static_cast<int>(fourth_orbits.size())) {
            throw std::invalid_argument(
                "fourth-center orbit index is outside the branch range");
        }
        if (options.fourth_orbit >= 0 &&
            (options.fifth_orbit >= 0 ||
             options.list_fifth_orbits)) {
            const int anchor = anchor_word(options.anchor_weight);
            const int third =
                orbits[static_cast<std::size_t>(options.third_orbit)]
                    .representative;
            const int fourth =
                fourth_orbits[static_cast<std::size_t>(
                    options.fourth_orbit)]
                    .representative;
            fifth_forbidden = fourth_forbidden;
            for (int orbit = 0; orbit < options.fourth_orbit; ++orbit) {
                const auto& members =
                    fourth_orbits[static_cast<std::size_t>(orbit)].members;
                fifth_forbidden.insert(
                    fifth_forbidden.end(),
                    members.begin(),
                    members.end());
            }
            fifth_orbits = center_orbits(
                options.anchor_weight,
                {0, anchor, third, fourth},
                fifth_forbidden);
        }
        if (options.list_fifth_orbits) {
            for (std::size_t index = 0;
                 index < fifth_orbits.size();
                 ++index) {
                std::cout
                    << index << ' '
                    << ternary_cover::format_word(
                           fifth_orbits[index].representative)
                    << " orbit_size="
                    << fifth_orbits[index].members.size()
                    << '\n';
            }
            return 0;
        }
        if (options.fifth_orbit >=
            static_cast<int>(fifth_orbits.size())) {
            throw std::invalid_argument(
                "fifth-center orbit index is outside the branch range");
        }
        if (!options.orbit_path.empty() || options.list_next_orbits) {
            std::vector<int> fixed_words{
                0, anchor_word(options.anchor_weight)};
            std::vector<int> forbidden_words;
            for (int orbit_index : options.orbit_path) {
                const int candidate_max_weight =
                    fixed_words.size() == 2
                    ? third_candidate_max_weight(
                          options.anchor_weight)
                    : options.anchor_weight;
                auto level = center_orbits(
                    options.anchor_weight,
                    fixed_words,
                    forbidden_words,
                    candidate_max_weight);
                if (orbit_index < 0 ||
                    orbit_index >= static_cast<int>(level.size())) {
                    throw std::invalid_argument(
                        "generic orbit-path index is outside its branch range");
                }
                const int representative =
                    level[static_cast<std::size_t>(orbit_index)]
                        .representative;
                path_orbits.push_back(std::move(level));
                path_representatives.push_back(representative);
                fixed_words.push_back(representative);
                const auto& selected_level = path_orbits.back();
                for (int orbit = 0; orbit < orbit_index; ++orbit) {
                    const auto& members =
                        selected_level[static_cast<std::size_t>(orbit)]
                            .members;
                    forbidden_words.insert(
                        forbidden_words.end(),
                        members.begin(),
                        members.end());
                }
            }
            if (options.list_next_orbits) {
                const int candidate_max_weight =
                    fixed_words.size() == 2
                    ? third_candidate_max_weight(
                          options.anchor_weight)
                    : options.anchor_weight;
                const auto next = center_orbits(
                    options.anchor_weight,
                    fixed_words,
                    forbidden_words,
                    candidate_max_weight);
                for (std::size_t index = 0; index < next.size(); ++index) {
                    std::cout
                        << index << ' '
                        << ternary_cover::format_word(
                               next[index].representative)
                        << " orbit_size="
                        << next[index].members.size()
                        << '\n';
                }
                return 0;
            }
        }

        std::vector<int> symmetry_fixed_centers;
        if (options.fix_zero) {
            symmetry_fixed_centers.push_back(0);
        }
        if (options.anchor_weight >= 0) {
            symmetry_fixed_centers.push_back(
                anchor_word(options.anchor_weight));
        }
        if (options.third_orbit >= 0) {
            symmetry_fixed_centers.push_back(
                orbits[static_cast<std::size_t>(options.third_orbit)]
                    .representative);
        }
        if (options.fourth_orbit >= 0) {
            symmetry_fixed_centers.push_back(
                fourth_orbits[static_cast<std::size_t>(
                    options.fourth_orbit)]
                    .representative);
        }
        if (options.fifth_orbit >= 0) {
            symmetry_fixed_centers.push_back(
                fifth_orbits[static_cast<std::size_t>(
                    options.fifth_orbit)]
                    .representative);
        }
        symmetry_fixed_centers.insert(
            symmetry_fixed_centers.end(),
            path_representatives.begin(),
            path_representatives.end());
        std::sort(
            symmetry_fixed_centers.begin(),
            symmetry_fixed_centers.end());
        symmetry_fixed_centers.erase(
            std::unique(
                symmetry_fixed_centers.begin(),
                symmetry_fixed_centers.end()),
            symmetry_fixed_centers.end());

        std::array<bool, ternary_cover::kSpaceSize> fixed_centers{};
        std::array<bool, ternary_cover::kSpaceSize> forbidden_centers{};
        for (int center = 0;
             center < ternary_cover::kSpaceSize;
             ++center) {
            forbidden_centers[static_cast<std::size_t>(center)] =
                ternary_cover::hamming_weight(center) >
                options.maximum_weight;
        }
        auto forbid_earlier_orbits = [&](const auto& orbit_list,
                                         int selected_orbit) {
            for (int orbit = 0; orbit < selected_orbit; ++orbit) {
                for (int center :
                     orbit_list[static_cast<std::size_t>(orbit)].members) {
                    forbidden_centers[
                        static_cast<std::size_t>(center)] = true;
                }
            }
        };
        if (options.third_orbit >= 0) {
            forbid_earlier_orbits(orbits, options.third_orbit);
        }
        if (options.fourth_orbit >= 0) {
            forbid_earlier_orbits(
                fourth_orbits, options.fourth_orbit);
        }
        if (options.fifth_orbit >= 0) {
            forbid_earlier_orbits(fifth_orbits, options.fifth_orbit);
        }
        for (std::size_t level = 0;
             level < options.orbit_path.size();
             ++level) {
            forbid_earlier_orbits(
                path_orbits[level], options.orbit_path[level]);
        }
        for (int center : symmetry_fixed_centers) {
            if (forbidden_centers[static_cast<std::size_t>(center)]) {
                throw std::logic_error(
                    "a symmetry-fixed center is also forbidden");
            }
            fixed_centers[static_cast<std::size_t>(center)] = true;
        }

        if (options.branch_manifest_json) {
            auto emit_centers = [&](const char* name, auto predicate) {
                std::cout << ",\"" << name << "\":[";
                bool first = true;
                for (int center = 0;
                     center < ternary_cover::kSpaceSize;
                     ++center) {
                    if (!predicate(center)) {
                        continue;
                    }
                    if (!first) {
                        std::cout << ',';
                    }
                    std::cout << center;
                    first = false;
                }
                std::cout << ']';
            };
            std::cout
                << "{\"schema\":1,\"anchor_weight\":"
                << options.anchor_weight
                << ",\"third_orbit\":" << options.third_orbit
                << ",\"representative\":\""
                << ternary_cover::format_word(
                       orbits[static_cast<std::size_t>(
                           options.third_orbit)]
                           .representative)
                << '"';
            emit_centers(
                "fixed_centers",
                [&](int center) {
                    return fixed_centers[
                        static_cast<std::size_t>(center)];
                });
            emit_centers(
                "forbidden_centers",
                [&](int center) {
                    return forbidden_centers[
                        static_cast<std::size_t>(center)];
                });
            emit_centers(
                "admissible_centers",
                [&](int center) {
                    return !fixed_centers[
                               static_cast<std::size_t>(center)] &&
                           !forbidden_centers[
                               static_cast<std::size_t>(center)];
                });
            std::cout << "}\n";
            return 0;
        }

        int uncovered_point_clauses = 0;
        for (int point = 0; point < ternary_cover::kSpaceSize; ++point) {
            std::vector<int> clause;
            clause.reserve(ternary_cover::kBallSize);
            bool covered_by_fixed_center = false;
            for (int center :
                 geometry.balls[static_cast<std::size_t>(point)]) {
                if (fixed_centers[static_cast<std::size_t>(center)]) {
                    covered_by_fixed_center = true;
                    break;
                }
                if (!forbidden_centers[
                        static_cast<std::size_t>(center)]) {
                    clause.push_back(selection_variable(center));
                }
            }
            if (!covered_by_fixed_center) {
                cnf.add(std::move(clause));
                ++uncovered_point_clauses;
            }
        }

        std::vector<int> selection_literals;
        selection_literals.reserve(ternary_cover::kSpaceSize);
        for (int center = 0; center < ternary_cover::kSpaceSize; ++center) {
            if (!fixed_centers[static_cast<std::size_t>(center)] &&
                !forbidden_centers[static_cast<std::size_t>(center)]) {
                selection_literals.push_back(
                    selection_variable(center));
            }
        }
        const int remaining_centers =
            options.centers -
            static_cast<int>(symmetry_fixed_centers.size());
        if (remaining_centers < 0 ||
            remaining_centers >
            static_cast<int>(selection_literals.size())) {
            throw std::logic_error(
                "fixed-center count is incompatible with cardinality");
        }
        add_between(
            cnf,
            selection_literals,
            options.exact ? remaining_centers : 0,
            remaining_centers);

        if (options.structural_constraints) {
            for (int coordinate = 0;
                 coordinate < ternary_cover::kLength;
                 ++coordinate) {
                for (int symbol = 0;
                     symbol < ternary_cover::kAlphabet;
                     ++symbol) {
                    std::vector<int> symbol_class;
                    symbol_class.reserve(
                        ternary_cover::kSpaceSize /
                        ternary_cover::kAlphabet);
                    for (int center = 0;
                         center < ternary_cover::kSpaceSize;
                         ++center) {
                        const auto digits = ternary_cover::decode(center);
                        if (digits[static_cast<std::size_t>(coordinate)] ==
                            symbol) {
                            symbol_class.push_back(
                                selection_variable(center));
                        }
                    }
                    add_between(cnf, symbol_class, 3, 10);
                }
            }
            add_far_center_cuts(cnf);
        }
        if (options.antipodal_cuts) {
            for (int center : symmetry_fixed_centers) {
                add_fixed_antipodal_cut(cnf, center);
            }
        }
        if (options.radial_sphere_cuts) {
            add_radial_sphere_cuts(cnf);
        }
        if (options.projection_cuts) {
            add_projection_cuts(cnf);
        }
        if (options.four_projection_cuts) {
            add_four_projection_cuts(cnf);
        }
        if (options.five_projection_cuts) {
            add_five_projection_cuts(cnf);
        }

        for (int center = 0;
             center < ternary_cover::kSpaceSize;
             ++center) {
            if (fixed_centers[static_cast<std::size_t>(center)]) {
                cnf.add({selection_variable(center)});
            } else if (
                forbidden_centers[static_cast<std::size_t>(center)]) {
                cnf.add({-selection_variable(center)});
            }
        }

        std::cout << "c K_3(6,2) radius-2 covering formulation\n";
        std::cout << "c selection variable for center w is 1 + base3(w)\n";
        std::cout << "c "
                  << (options.exact ? "exactly " : "at most ")
                  << options.centers << " centers\n";
        std::cout
            << "c reduced branch core: "
            << symmetry_fixed_centers.size()
            << " fixed centers, "
            << std::count(
                   forbidden_centers.begin(),
                   forbidden_centers.end(),
                   true)
            << " forbidden centers, "
            << uncovered_point_clauses
            << " unresolved point clauses\n";
        if (options.fix_zero) {
            std::cout << "c center 000000 fixed by translation symmetry\n";
        }
        if (options.anchor_weight >= 0) {
            std::cout << "c normalized maximum-weight anchor "
                      << ternary_cover::format_word(
                             anchor_word(options.anchor_weight))
                      << '\n';
            if (options.anchor_weight >= 5 &&
                (options.third_orbit >= 0 ||
                 !options.orbit_path.empty())) {
                std::cout
                    << "c third-center branching restricted to weight at "
                    << "most 4 by radius-3 capacity\n";
            }
        }
        if (options.structural_constraints) {
            std::cout
                << "c symbol counts 3 through 10 and far-neighbor cuts\n";
        }
        if (options.projection_cuts) {
            std::cout
                << "c all 135 two-coordinate capacity inequalities enabled\n";
        }
        if (options.four_projection_cuts) {
            std::cout
                << "c all 1215 four-coordinate capacity inequalities enabled\n";
        }
        if (options.five_projection_cuts) {
            std::cout
                << "c all 1458 five-coordinate capacity inequalities enabled\n";
        }
        if (options.antipodal_cuts) {
            std::cout
                << "c antipodal capacity cuts at "
                << symmetry_fixed_centers.size()
                << " symmetry-fixed centers enabled\n";
        }
        if (options.radial_sphere_cuts) {
            std::cout
                << "c all 1458 radial distance-1 and distance-2 cuts enabled\n";
        }
        if (options.fourth_orbit >= 0) {
            std::cout << "c earliest occupied fourth-center orbit "
                      << options.fourth_orbit << " represented by "
                      << ternary_cover::format_word(
                             fourth_orbits[static_cast<std::size_t>(
                                 options.fourth_orbit)]
                                 .representative)
                      << '\n';
        }
        if (options.fifth_orbit >= 0) {
            std::cout << "c earliest occupied fifth-center orbit "
                      << options.fifth_orbit << " represented by "
                      << ternary_cover::format_word(
                             fifth_orbits[static_cast<std::size_t>(
                                 options.fifth_orbit)]
                                 .representative)
                      << '\n';
        }
        if (!options.orbit_path.empty()) {
            std::cout << "c generic stabilizer-orbit path";
            for (std::size_t level = 0;
                 level < options.orbit_path.size();
                 ++level) {
                std::cout << ' ' << options.orbit_path[level] << ':'
                          << ternary_cover::format_word(
                                 path_representatives[level]);
            }
            std::cout << '\n';
        }
        if (options.third_orbit >= 0) {
            std::cout << "c earliest occupied third-center orbit "
                      << options.third_orbit << " represented by "
                      << ternary_cover::format_word(
                             orbits[static_cast<std::size_t>(
                                 options.third_orbit)]
                                 .representative)
                      << '\n';
        }
        std::cout << "p cnf " << cnf.variables << ' '
                  << cnf.clauses.size() << '\n';
        for (const std::vector<int>& clause : cnf.clauses) {
            for (int literal : clause) {
                std::cout << literal << ' ';
            }
            std::cout << "0\n";
        }
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
