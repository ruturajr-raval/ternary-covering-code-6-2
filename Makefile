CXX ?= c++
CXXFLAGS ?= -std=c++20 -O3 -Wall -Wextra -Wpedantic -pthread
CPPFLAGS ?= -Isrc
CP_SAT_PYTHON ?= .tools/ortools-venv/bin/python

BUILD_DIR := build
BINARIES := \
	$(BUILD_DIR)/verify_code \
	$(BUILD_DIR)/search_code \
	$(BUILD_DIR)/compress_code \
	$(BUILD_DIR)/repair_code \
	$(BUILD_DIR)/generate_cnf

.PHONY: all clean test test-cp-sat

all: $(BINARIES)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/verify_code: src/verify_code.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

$(BUILD_DIR)/search_code: src/search_code.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

$(BUILD_DIR)/compress_code: src/compress_code.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

$(BUILD_DIR)/repair_code: src/repair_code.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

$(BUILD_DIR)/generate_cnf: src/generate_cnf.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

test: all
	bash tests/test_cli.sh

test-cp-sat: all
	$(CP_SAT_PYTHON) tests/test_cp_sat_geometry.py

clean:
	rm -f $(BINARIES)
