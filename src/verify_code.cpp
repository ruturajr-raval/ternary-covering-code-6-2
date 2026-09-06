#include "ternary_cover.hpp"

#include <iostream>
#include <string>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::cerr << "usage: verify_code CODE_FILE\n";
        return 2;
    }

    try {
        const ternary_cover::Geometry geometry;
        const std::vector<int> centers = ternary_cover::read_code(argv[1]);
        const ternary_cover::Verification result =
            ternary_cover::verify_code(geometry, centers);

        std::cout << "centers: " << centers.size() << '\n';
        std::cout << "distinct: " << (result.distinct ? "yes" : "no") << '\n';
        std::cout << "holes: " << result.holes << '\n';
        std::cout << "minimum multiplicity: "
                  << result.minimum_multiplicity << '\n';
        std::cout << "maximum multiplicity: "
                  << result.maximum_multiplicity << '\n';
        std::cout << "multiplicity histogram:";
        for (std::size_t i = 0;
             i < result.multiplicity_histogram.size();
             ++i) {
            if (result.multiplicity_histogram[i] != 0) {
                std::cout << ' ' << i << ':'
                          << result.multiplicity_histogram[i];
            }
        }
        std::cout << '\n';

        if (!result.uncovered.empty()) {
            std::cout << "first uncovered words:";
            const std::size_t limit =
                std::min<std::size_t>(result.uncovered.size(), 20);
            for (std::size_t i = 0; i < limit; ++i) {
                std::cout << ' '
                          << ternary_cover::format_word(result.uncovered[i]);
            }
            std::cout << '\n';
        }

        return result.distinct && result.holes == 0 ? 0 : 1;
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n';
        return 2;
    }
}

