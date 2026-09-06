#!/usr/bin/env python3

from itertools import product
from pathlib import Path
import sys


LENGTH = 6
SPACE_SIZE = 3 ** LENGTH


def decode(value):
    digits = [0] * LENGTH
    for index in range(LENGTH - 1, -1, -1):
        digits[index] = value % 3
        value //= 3
    return tuple(digits)


WORDS = tuple(decode(value) for value in range(SPACE_SIZE))


def encode(word):
    value = 0
    for digit in word:
        value = 3 * value + digit
    return value


def distance(left, right):
    return sum(a != b for a, b in zip(left, right))


def weight(word):
    return sum(digit != 0 for digit in word)


def expected_reduced_coverage():
    fixed = {
        encode((0, 0, 0, 0, 0, 0)),
        encode((1, 1, 1, 1, 1, 0)),
    }
    forbidden = {
        center
        for center, word in enumerate(WORDS)
        if weight(word) > 5
    }
    clauses = []
    for point, point_word in enumerate(WORDS):
        ball = [
            center
            for center, center_word in enumerate(WORDS)
            if distance(point_word, center_word) <= 2
        ]
        if fixed.intersection(ball):
            continue
        clauses.append(
            tuple(
                center + 1
                for center in ball
                if center not in forbidden and center not in fixed
            )
        )
    return fixed, forbidden, clauses


def parse_and_check(path):
    fixed, forbidden, expected_coverage = expected_reduced_coverage()
    assert len(forbidden) == 64
    assert len(expected_coverage) == 583

    header = None
    clause_count = 0
    selection_units = set()
    with path.open() as handle:
        for line in handle:
            if line.startswith("c "):
                continue
            if line.startswith("p cnf "):
                fields = line.split()
                assert len(fields) == 4
                header = (int(fields[2]), int(fields[3]))
                continue
            assert header is not None
            literals = tuple(int(token) for token in line.split())
            assert literals and literals[-1] == 0
            clause = literals[:-1]
            assert all(
                literal != 0 and abs(literal) <= header[0]
                for literal in clause
            )
            if clause_count < len(expected_coverage):
                assert clause == expected_coverage[clause_count]
            if len(clause) == 1 and abs(clause[0]) <= SPACE_SIZE:
                selection_units.add(clause[0])
            clause_count += 1

    assert header is not None
    assert clause_count == header[1]
    expected_units = {
        center + 1
        for center in fixed
    } | {
        -(center + 1)
        for center in forbidden
    }
    assert selection_units == expected_units


def check_antipodal_capacities():
    antipodes = tuple(product((1, 2), repeat=LENGTH))
    capacities = []
    for center_distance in (4, 5, 6):
        center = (
            (1,) * center_distance
            + (0,) * (LENGTH - center_distance)
        )
        capacities.append(
            sum(distance(center, word) <= 2 for word in antipodes)
        )
    assert tuple(capacities) == (4, 12, 22)


if len(sys.argv) != 2:
    raise SystemExit("usage: test_cnf_semantics.py CNF")

parse_and_check(Path(sys.argv[1]))
check_antipodal_capacities()
print("CNF semantic tests passed")
