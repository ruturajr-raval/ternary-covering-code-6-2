#include <algorithm>
#include <array>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <tuple>
#include <vector>

namespace {

constexpr int kLength = 6;
constexpr int kAlphabet = 3;
constexpr int kRadius = 2;
constexpr int kSpaceSize = 729;
constexpr int kTargetCenters = 16;

using Word = std::array<int, kLength>;
using ThirdOrbitKey = std::array<int, 4>;

struct WeightEntry {
    std::string key;
    int weight;
    int orbit_size;
};

struct Certificate {
    int anchor_weight;
    int third_orbit;
    std::string representative;
    int expected_admissible_centers;
    int expected_holes;
    int expected_total_weight;
    int expected_max_capacity;
    std::vector<WeightEntry> weights;
};

Word decode(int value) {
    Word word{};
    for (int index = kLength - 1; index >= 0; --index) {
        word[static_cast<std::size_t>(index)] = value % kAlphabet;
        value /= kAlphabet;
    }
    return word;
}

int encode(const Word& word) {
    int value = 0;
    for (int digit : word) {
        value = kAlphabet * value + digit;
    }
    return value;
}

int distance(const Word& left, const Word& right) {
    int result = 0;
    for (int index = 0; index < kLength; ++index) {
        result += left[static_cast<std::size_t>(index)] !=
                  right[static_cast<std::size_t>(index)];
    }
    return result;
}

int weight(const Word& word) {
    return static_cast<int>(std::count_if(
        word.begin(), word.end(), [](int digit) { return digit != 0; }));
}

std::string format_word(const Word& word) {
    std::string result;
    result.reserve(kLength);
    for (int digit : word) {
        result.push_back(static_cast<char>('0' + digit));
    }
    return result;
}

Word anchor_word(int anchor_weight) {
    Word word{};
    std::fill_n(word.begin(), anchor_weight, 1);
    return word;
}

ThirdOrbitKey third_orbit_key(
    const Word& word,
    int anchor_weight) {
    ThirdOrbitKey key{};
    for (int index = 0; index < anchor_weight; ++index) {
        ++key[static_cast<std::size_t>(
            word[static_cast<std::size_t>(index)])];
    }
    for (int index = anchor_weight; index < kLength; ++index) {
        key[3] += word[static_cast<std::size_t>(index)] != 0;
    }
    return key;
}

std::vector<std::pair<int, std::vector<int>>> third_orbits(
    const std::array<Word, kSpaceSize>& words,
    int anchor_weight) {
    const Word zero{};
    const Word anchor = anchor_word(anchor_weight);
    const int candidate_max_weight = std::min(anchor_weight, 4);
    std::map<ThirdOrbitKey, std::vector<int>> groups;
    for (int center = 0; center < kSpaceSize; ++center) {
        const Word& word = words[static_cast<std::size_t>(center)];
        if (word == zero ||
            word == anchor ||
            weight(word) > candidate_max_weight) {
            continue;
        }
        groups[third_orbit_key(word, anchor_weight)].push_back(center);
    }

    std::vector<std::pair<int, std::vector<int>>> result;
    for (auto& [key, members] : groups) {
        static_cast<void>(key);
        std::sort(members.begin(), members.end());
        result.emplace_back(members.front(), std::move(members));
    }
    std::sort(result.begin(), result.end());
    return result;
}

std::string count_block(
    const Word& point,
    const Word& representative,
    int representative_symbol,
    int coordinate_limit) {
    std::array<int, kAlphabet> counts{};
    for (int coordinate = 0;
         coordinate < coordinate_limit;
         ++coordinate) {
        if (representative[static_cast<std::size_t>(coordinate)] ==
            representative_symbol) {
            ++counts[static_cast<std::size_t>(
                point[static_cast<std::size_t>(coordinate)])];
        }
    }
    std::string result;
    for (int count : counts) {
        result.push_back(static_cast<char>('0' + count));
    }
    return result;
}

std::string certificate_key(
    const Word& point,
    const Word& representative,
    int anchor_weight) {
    if (anchor_weight == 5) {
        return
            count_block(point, representative, 0, 5) + "|" +
            count_block(point, representative, 1, 5) + "|" +
            count_block(point, representative, 2, 5) + "|" +
            (point[5] == 0 ? "0" : "1");
    }
    if (anchor_weight == 6) {
        return
            count_block(point, representative, 0, 6) + "|" +
            count_block(point, representative, 2, 6);
    }
    throw std::logic_error("unsupported anchor weight");
}

std::vector<Certificate> certificates() {
    return {
        {
            5, 19, "011110", 270, 549, 80, 6,
            {
                {"001|202|000|0", 1, 6},
                {"001|310|000|1", 2, 8},
                {"010|202|000|0", 1, 6},
                {"010|310|000|1", 2, 8},
                {"100|202|000|1", 1, 12},
                {"100|211|000|1", 1, 24},
            },
        },
        {
            5, 20, "011120", 265, 541, 40, 3,
            {
                {"001|300|001|1", 2, 2},
                {"001|300|010|1", 2, 2},
                {"010|300|001|1", 2, 2},
                {"010|300|010|1", 2, 2},
                {"100|102|100|1", 1, 6},
                {"100|111|100|1", 1, 12},
                {"100|120|100|1", 1, 6},
            },
        },
        {
            5, 21, "011220", 245, 528, 40, 3,
            {
                {"001|101|200|1", 1, 4},
                {"001|110|200|1", 1, 4},
                {"010|101|200|1", 1, 4},
                {"010|110|200|1", 1, 4},
                {"100|002|200|1", 1, 2},
                {"100|011|200|1", 1, 4},
                {"100|020|200|1", 1, 2},
                {"100|200|002|1", 2, 2},
                {"100|200|011|1", 2, 4},
                {"100|200|020|1", 2, 2},
            },
        },
        {
            5, 22, "012220", 215, 522, 40, 3,
            {
                {"001|001|300|1", 2, 2},
                {"001|010|300|1", 2, 2},
                {"010|001|300|1", 2, 2},
                {"010|010|300|1", 2, 2},
                {"100|100|102|1", 1, 6},
                {"100|100|111|1", 1, 12},
                {"100|100|120|1", 1, 6},
            },
        },
        {
            5, 23, "022220", 195, 516, 80, 6,
            {
                {"001|000|211|0", 1, 12},
                {"001|000|301|1", 2, 8},
                {"010|000|211|0", 1, 12},
                {"010|000|301|1", 2, 8},
                {"100|000|121|0", 1, 12},
                {"100|000|220|1", 1, 12},
            },
        },
        {
            6, 13, "002222", 269, 516, 132, 10,
            {
                {"002|301", 1, 4},
                {"002|310", 1, 4},
                {"011|310", 1, 8},
                {"020|301", 1, 4},
                {"101|202", 1, 12},
                {"101|211", 1, 24},
                {"101|220", 1, 12},
                {"110|211", 2, 24},
                {"200|121", 1, 12},
                {"200|130", 1, 4},
            },
        },
    };
}

void dump_certificate_data(
    const std::vector<Certificate>& all_certificates) {
    std::cout << "schema 1\n";
    std::cout << "target_centers " << kTargetCenters << '\n';
    for (const Certificate& certificate : all_certificates) {
        std::cout
            << "branch "
            << certificate.anchor_weight << ' '
            << certificate.third_orbit << ' '
            << certificate.representative << ' '
            << certificate.expected_admissible_centers << ' '
            << certificate.expected_holes << ' '
            << certificate.expected_total_weight << ' '
            << certificate.expected_max_capacity << '\n';
        for (const WeightEntry& entry : certificate.weights) {
            std::cout
                << "weight " << entry.key << ' '
                << entry.weight << ' '
                << entry.orbit_size << '\n';
        }
        std::cout << "end\n";
    }
}

std::string verify_certificate(
    const Certificate& certificate,
    const std::array<Word, kSpaceSize>& words) {
    const auto orbits =
        third_orbits(words, certificate.anchor_weight);
    if (certificate.third_orbit < 0 ||
        certificate.third_orbit >= static_cast<int>(orbits.size())) {
        throw std::logic_error("third orbit is outside the branch range");
    }
    const int representative =
        orbits[static_cast<std::size_t>(
            certificate.third_orbit)].first;
    const Word& representative_word =
        words[static_cast<std::size_t>(representative)];
    if (format_word(representative_word) !=
        certificate.representative) {
        throw std::logic_error("third-center representative mismatch");
    }

    std::array<bool, kSpaceSize> fixed{};
    fixed[0] = true;
    fixed[static_cast<std::size_t>(
        encode(anchor_word(certificate.anchor_weight)))] = true;
    fixed[static_cast<std::size_t>(representative)] = true;
    if (std::count(fixed.begin(), fixed.end(), true) != 3) {
        throw std::logic_error("certificate branch must fix three centers");
    }

    std::array<bool, kSpaceSize> forbidden{};
    for (int center = 0; center < kSpaceSize; ++center) {
        forbidden[static_cast<std::size_t>(center)] =
            weight(words[static_cast<std::size_t>(center)]) >
            certificate.anchor_weight;
    }
    for (int orbit = 0;
         orbit < certificate.third_orbit;
         ++orbit) {
        for (int center :
             orbits[static_cast<std::size_t>(orbit)].second) {
            forbidden[static_cast<std::size_t>(center)] = true;
        }
    }
    for (int center = 0; center < kSpaceSize; ++center) {
        if (fixed[static_cast<std::size_t>(center)] &&
            forbidden[static_cast<std::size_t>(center)]) {
            throw std::logic_error("a fixed center is forbidden");
        }
    }

    std::vector<int> admissible;
    for (int center = 0; center < kSpaceSize; ++center) {
        if (!fixed[static_cast<std::size_t>(center)] &&
            !forbidden[static_cast<std::size_t>(center)]) {
            admissible.push_back(center);
        }
    }
    if (static_cast<int>(admissible.size()) !=
        certificate.expected_admissible_centers) {
        throw std::logic_error("admissible-center count mismatch");
    }

    std::vector<int> holes;
    for (int point = 0; point < kSpaceSize; ++point) {
        bool covered = false;
        for (int center = 0; center < kSpaceSize; ++center) {
            if (fixed[static_cast<std::size_t>(center)] &&
                distance(
                    words[static_cast<std::size_t>(point)],
                    words[static_cast<std::size_t>(center)]) <=
                    kRadius) {
                covered = true;
                break;
            }
        }
        if (!covered) {
            holes.push_back(point);
        }
    }
    if (static_cast<int>(holes.size()) !=
        certificate.expected_holes) {
        throw std::logic_error("hole count mismatch");
    }

    std::map<std::string, WeightEntry> entries;
    for (const WeightEntry& entry : certificate.weights) {
        if (entry.weight <= 0 ||
            !entries.emplace(entry.key, entry).second) {
            throw std::logic_error("invalid certificate weight entry");
        }
    }

    std::map<std::string, std::vector<int>> ambient_by_key;
    for (int point = 0; point < kSpaceSize; ++point) {
        const std::string key = certificate_key(
            words[static_cast<std::size_t>(point)],
            representative_word,
            certificate.anchor_weight);
        if (entries.contains(key)) {
            ambient_by_key[key].push_back(point);
        }
    }
    std::set<int> hole_set(holes.begin(), holes.end());
    for (const auto& [key, entry] : entries) {
        const auto found = ambient_by_key.find(key);
        if (found == ambient_by_key.end() ||
            static_cast<int>(found->second.size()) !=
                entry.orbit_size) {
            throw std::logic_error("certificate orbit size mismatch");
        }
        if (!std::all_of(
                found->second.begin(),
                found->second.end(),
                [&](int point) { return hole_set.contains(point); })) {
            throw std::logic_error(
                "positive-weight orbit contains a non-hole");
        }
    }

    std::array<int, kSpaceSize> point_weights{};
    int total_weight = 0;
    for (int point : holes) {
        const std::string key = certificate_key(
            words[static_cast<std::size_t>(point)],
            representative_word,
            certificate.anchor_weight);
        const auto found = entries.find(key);
        if (found != entries.end()) {
            point_weights[static_cast<std::size_t>(point)] =
                found->second.weight;
            total_weight += found->second.weight;
        }
    }
    if (total_weight != certificate.expected_total_weight) {
        throw std::logic_error("total certificate weight mismatch");
    }

    int max_capacity = 0;
    int max_capacity_centers = 0;
    for (int center : admissible) {
        int capacity = 0;
        for (int point : holes) {
            if (distance(
                    words[static_cast<std::size_t>(point)],
                    words[static_cast<std::size_t>(center)]) <=
                    kRadius) {
                capacity +=
                    point_weights[static_cast<std::size_t>(point)];
            }
        }
        if (capacity > max_capacity) {
            max_capacity = capacity;
            max_capacity_centers = 1;
        } else if (capacity == max_capacity) {
            ++max_capacity_centers;
        }
    }
    if (max_capacity != certificate.expected_max_capacity) {
        throw std::logic_error("maximum center capacity mismatch");
    }

    const int remaining_centers = kTargetCenters - 3;
    const int upper_bound = remaining_centers * max_capacity;
    if (total_weight <= upper_bound) {
        throw std::logic_error(
            "certificate does not prove a contradiction");
    }

    std::ostringstream output;
    output
        << 'w' << certificate.anchor_weight
        << " orbit ";
    if (certificate.third_orbit < 10) {
        output << '0';
    }
    output
        << certificate.third_orbit << ' '
        << certificate.representative
        << ": |U|=" << admissible.size()
        << " |H|=" << holes.size()
        << " W=" << total_weight
        << " Q=" << max_capacity
        << " 13Q=" << upper_bound
        << " margin=" << total_weight - upper_bound;
    static_cast<void>(max_capacity_centers);
    return output.str();
}

}  // namespace

int main(int argc, char** argv) {
    try {
        const bool dump_data =
            argc == 2 &&
            std::string(argv[1]) == "--dump-certificate-data";
        if (argc > 1 && !dump_data) {
            throw std::invalid_argument(
                "usage: verify_branch_certificates "
                "[--dump-certificate-data]");
        }
        const auto all_certificates = certificates();
        if (all_certificates.size() != 6) {
            throw std::logic_error(
                "expected exactly six branch certificates");
        }
        if (dump_data) {
            dump_certificate_data(all_certificates);
            return 0;
        }

        std::array<Word, kSpaceSize> words{};
        for (int value = 0; value < kSpaceSize; ++value) {
            words[static_cast<std::size_t>(value)] = decode(value);
        }
        for (const Certificate& certificate : all_certificates) {
            std::cout << verify_certificate(certificate, words) << '\n';
        }
        std::cout << "all weighted branch certificates verified\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}
