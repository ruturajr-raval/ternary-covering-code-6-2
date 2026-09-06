CXX ?= c++
CXXFLAGS ?= -std=c++20 -O3 -Wall -Wextra -Wpedantic -pthread
CPPFLAGS ?= -Isrc
CP_SAT_PYTHON ?= .tools/ortools-venv/bin/python
PYTHON ?= python3

BUILD_DIR := build
BINARIES := \
	$(BUILD_DIR)/verify_code \
	$(BUILD_DIR)/search_code \
	$(BUILD_DIR)/compress_code \
	$(BUILD_DIR)/repair_code \
	$(BUILD_DIR)/verify_branch_certificates \
	$(BUILD_DIR)/generate_cnf

.PHONY: all clean test test-cp-sat paper-build paper-bundle release-manifest verify-release-manifest verify-release-assets

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

$(BUILD_DIR)/verify_branch_certificates: src/verify_branch_certificates.cpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

$(BUILD_DIR)/generate_cnf: src/generate_cnf.cpp src/ternary_cover.hpp | $(BUILD_DIR)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $< -o $@

test: all
	PYTHON="$(PYTHON)" bash tests/test_cli.sh
	$(PYTHON) -m unittest \
		tests.test_release_tools \
		tests.test_publication_metadata \
		-v

test-cp-sat: all
	$(CP_SAT_PYTHON) tests/test_cp_sat_geometry.py

paper-build:
	mkdir -p build/paper
	latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
		-output-directory=build/paper paper/main.tex

paper-bundle:
	$(PYTHON) tools/build_paper_bundle.py

release-manifest:
	$(PYTHON) tools/build_release_manifest.py

verify-release-manifest:
	$(PYTHON) tools/verify_checksum_manifest.py

verify-release-assets:
	$(PYTHON) tools/verify_release_assets.py

clean:
	rm -f $(BINARIES)
