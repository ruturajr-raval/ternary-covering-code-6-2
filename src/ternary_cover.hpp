#ifndef TERNARY_COVER_HPP
#define TERNARY_COVER_HPP

#include <algorithm>
#include <array>
#include <bitset>
#include <cctype>
#include <cstdint>
#include <fstream>
#include <limits>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace ternary_cover {

inline constexpr int kAlphabet = 3;
inline constexpr int kLength = 6;
inline constexpr int kRadius = 2;
inline constexpr int kSpaceSize = 729;
inline constexpr int kBallSize = 73;

using Digits = std::array<std::uint8_t, kLength>;
using Mask = std::bitset<kSpaceSize>;

inline Digits decode(int word) {
    if (word < 0 || word >= kSpaceSize) {
        throw std::out_of_range("word is outside the ternary length-6 space");
    }
    Digits digits{};
    for (int i = kLength - 1; i >= 0; --i) {
        digits[static_cast<std::size_t>(i)] =
            static_cast<std::uint8_t>(word % kAlphabet);
        word /= kAlphabet;
    }
    return digits;
}

inline int encode(const Digits& digits) {
    int word = 0;
    for (std::uint8_t digit : digits) {
        if (digit >= kAlphabet) {
            throw std::invalid_argument("digit is not ternary");
        }
        word = word * kAlphabet + static_cast<int>(digit);
    }
    return word;
}

inline std::string format_word(int word) {
    const Digits digits = decode(word);
    std::string text;
    text.reserve(kLength);
    for (std::uint8_t digit : digits) {
        text.push_back(static_cast<char>('0' + digit));
    }
    return text;
}

inline int parse_word(std::string_view text) {
    if (text.size() != kLength) {
        throw std::invalid_argument("each word must contain exactly six digits");
    }
    Digits digits{};
    for (int i = 0; i < kLength; ++i) {
        const char ch = text[static_cast<std::size_t>(i)];
        if (ch < '0' || ch > '2') {
            throw std::invalid_argument("word contains a non-ternary digit");
        }
        digits[static_cast<std::size_t>(i)] =
            static_cast<std::uint8_t>(ch - '0');
    }
    return encode(digits);
}

inline int hamming_distance(int lhs, int rhs) {
    const Digits a = decode(lhs);
    const Digits b = decode(rhs);
    int distance = 0;
    for (int i = 0; i < kLength; ++i) {
        distance += a[static_cast<std::size_t>(i)] !=
                    b[static_cast<std::size_t>(i)];
    }
    return distance;
}

inline int hamming_weight(int word) {
    const Digits digits = decode(word);
    int weight = 0;
    for (std::uint8_t digit : digits) {
        weight += digit != 0;
    }
    return weight;
}

struct Geometry {
    std::array<std::array<int, kBallSize>, kSpaceSize> balls{};
    std::array<Mask, kSpaceSize> masks{};

    Geometry() {
        for (int center = 0; center < kSpaceSize; ++center) {
            int cursor = 0;
            for (int point = 0; point < kSpaceSize; ++point) {
                if (hamming_distance(center, point) <= kRadius) {
                    if (cursor >= kBallSize) {
                        throw std::logic_error("radius-2 ball is too large");
                    }
                    balls[static_cast<std::size_t>(center)]
                         [static_cast<std::size_t>(cursor)] = point;
                    masks[static_cast<std::size_t>(center)].set(
                        static_cast<std::size_t>(point));
                    ++cursor;
                }
            }
            if (cursor != kBallSize) {
                throw std::logic_error("radius-2 ball has the wrong size");
            }
        }
    }
};

struct Verification {
    bool distinct = true;
    int holes = 0;
    int minimum_multiplicity = std::numeric_limits<int>::max();
    int maximum_multiplicity = 0;
    std::array<int, 18> multiplicity_histogram{};
    std::vector<int> uncovered;
};

inline Verification verify_code(
    const Geometry& geometry,
    const std::vector<int>& centers) {
    Verification result;
    std::array<int, kSpaceSize> multiplicity{};
    std::array<bool, kSpaceSize> seen{};

    for (int center : centers) {
        if (center < 0 || center >= kSpaceSize) {
            throw std::out_of_range("code contains an invalid center");
        }
        if (seen[static_cast<std::size_t>(center)]) {
            result.distinct = false;
        }
        seen[static_cast<std::size_t>(center)] = true;
        for (int point :
             geometry.balls[static_cast<std::size_t>(center)]) {
            ++multiplicity[static_cast<std::size_t>(point)];
        }
    }

    for (int point = 0; point < kSpaceSize; ++point) {
        const int value = multiplicity[static_cast<std::size_t>(point)];
        result.minimum_multiplicity =
            std::min(result.minimum_multiplicity, value);
        result.maximum_multiplicity =
            std::max(result.maximum_multiplicity, value);
        if (value < static_cast<int>(result.multiplicity_histogram.size())) {
            ++result.multiplicity_histogram[static_cast<std::size_t>(value)];
        }
        if (value == 0) {
            ++result.holes;
            result.uncovered.push_back(point);
        }
    }
    return result;
}

inline std::vector<int> read_code(const std::string& path) {
    std::ifstream input(path);
    if (!input) {
        throw std::runtime_error("cannot open code file: " + path);
    }

    std::vector<int> centers;
    std::string line;
    while (std::getline(input, line)) {
        const auto comment = line.find('#');
        if (comment != std::string::npos) {
            line.erase(comment);
        }
        line.erase(std::remove_if(line.begin(), line.end(), [](char ch) {
            return std::isspace(static_cast<unsigned char>(ch)) != 0;
        }), line.end());
        if (!line.empty()) {
            centers.push_back(parse_word(line));
        }
    }
    return centers;
}

inline void write_code(
    const std::string& path,
    const std::vector<int>& centers) {
    std::ofstream output(path);
    if (!output) {
        throw std::runtime_error("cannot write code file: " + path);
    }
    for (int center : centers) {
        output << format_word(center) << '\n';
    }
}

}  // namespace ternary_cover

#endif

