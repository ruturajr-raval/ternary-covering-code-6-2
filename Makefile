CXX ?= c++
CXXFLAGS ?= -std=c++20 -O3 -Wall -Wextra -Wpedantic -pthread
CPPFLAGS ?= -Isrc
CP_SAT_PYTHON ?= .tools/ortools-venv/bin/python
LATEXMK ?= latexmk
PYTHON ?= python3
SOURCE_DATE_EPOCH ?= 1788739200
TECTONIC ?= tectonic

BUILD_DIR := build
PAPER_PDF := dist/paper/ternary-covering-code-6-2-paper.pdf
PAPER_SOURCE := dist/paper/ternary-covering-code-6-2-source.tar.gz
RELEASE_DIR := dist/release
BINARIES := \
	$(BUILD_DIR)/verify_code \
	$(BUILD_DIR)/search_code \
	$(BUILD_DIR)/compress_code \
	$(BUILD_DIR)/repair_code \
	$(BUILD_DIR)/verify_branch_certificates \
	$(BUILD_DIR)/generate_cnf

.PHONY: all clean test test-cp-sat paper-build paper-bundle release-assets release-checksums release-manifest verify-release-manifest verify-release-manifest-worktree verify-release-assets

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
	if command -v "$(TECTONIC)" >/dev/null 2>&1; then \
		SOURCE_DATE_EPOCH="$(SOURCE_DATE_EPOCH)" \
			"$(TECTONIC)" -X compile paper/main.tex \
			--outdir build/paper --keep-logs; \
	elif command -v "$(LATEXMK)" >/dev/null 2>&1; then \
		SOURCE_DATE_EPOCH="$(SOURCE_DATE_EPOCH)" \
			"$(LATEXMK)" -pdf -interaction=nonstopmode -halt-on-error \
			-file-line-error -output-directory=build/paper paper/main.tex; \
	else \
		echo "paper-build requires latexmk or tectonic" >&2; \
		exit 127; \
	fi

paper-bundle:
	$(PYTHON) tools/build_paper_bundle.py

release-assets: paper-build paper-bundle
	rm -rf $(RELEASE_DIR)
	mkdir -p dist/paper $(RELEASE_DIR)
	cp build/paper/main.pdf $(PAPER_PDF)
	cp $(PAPER_PDF) $(PAPER_SOURCE) $(RELEASE_DIR)/
	cd $(RELEASE_DIR) && LC_ALL=C shasum -a 256 \
		$(notdir $(PAPER_PDF)) \
		$(notdir $(PAPER_SOURCE)) \
		> SHA256SUMS

release-checksums:
	test -s $(RELEASE_DIR)/SHA256SUMS
	cd $(RELEASE_DIR) && shasum -a 256 -c SHA256SUMS

release-manifest:
	$(PYTHON) tools/build_release_manifest.py

verify-release-manifest:
	$(PYTHON) tools/verify_checksum_manifest.py

verify-release-manifest-worktree:
	$(PYTHON) tools/verify_checksum_manifest.py --worktree

verify-release-assets:
	$(PYTHON) tools/verify_release_assets.py \
		--release-pdf $(RELEASE_DIR)/$(notdir $(PAPER_PDF)) \
		--release-source $(RELEASE_DIR)/$(notdir $(PAPER_SOURCE)) \
		--checksum-manifest $(RELEASE_DIR)/SHA256SUMS

clean:
	rm -f $(BINARIES)
