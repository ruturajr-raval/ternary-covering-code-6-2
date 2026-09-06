#!/usr/bin/env python3

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


LENGTH = 6
ALPHABET = 3
RADIUS = 2
SPACE_SIZE = ALPHABET ** LENGTH


def decode(value):
    digits = [0] * LENGTH
    for index in range(LENGTH - 1, -1, -1):
        digits[index] = value % ALPHABET
        value //= ALPHABET
    return tuple(digits)


WORDS = tuple(decode(value) for value in range(SPACE_SIZE))


def encode(word):
    value = 0
    for digit in word:
        value = ALPHABET * value + digit
    return value


def distance(left, right):
    return sum(a != b for a, b in zip(left, right))


DISTANCES = tuple(
    tuple(distance(left, right) for right in WORDS)
    for left in WORDS
)


def word_weight(word):
    return sum(digit != 0 for digit in word)


def format_word(word):
    return "".join(map(str, word))


def anchor_word(anchor_weight):
    return (1,) * anchor_weight + (0,) * (LENGTH - anchor_weight)


def third_candidate_max_weight(anchor_weight):
    return min(anchor_weight, 4)


def third_orbit_key(word, anchor_weight):
    support = word[:anchor_weight]
    return (
        support.count(0),
        support.count(1),
        support.count(2),
        sum(digit != 0 for digit in word[anchor_weight:]),
    )


def third_orbits(anchor_weight):
    anchor = anchor_word(anchor_weight)
    candidate_max_weight = third_candidate_max_weight(anchor_weight)
    groups = defaultdict(list)
    for center, word in enumerate(WORDS):
        if word == (0,) * LENGTH or word == anchor:
            continue
        if word_weight(word) > candidate_max_weight:
            continue
        groups[third_orbit_key(word, anchor_weight)].append(center)
    return tuple(
        sorted(
            (
                min(members, key=lambda center: WORDS[center]),
                tuple(sorted(members)),
            )
            for members in groups.values()
        )
    )


def branch_data(anchor_weight, orbit_index):
    orbits = third_orbits(anchor_weight)
    representative = orbits[orbit_index][0]
    fixed = {
        encode((0,) * LENGTH),
        encode(anchor_word(anchor_weight)),
        representative,
    }
    forbidden = {
        center
        for center, word in enumerate(WORDS)
        if word_weight(word) > anchor_weight
    }
    for _, members in orbits[:orbit_index]:
        forbidden.update(members)
    if fixed & forbidden:
        raise AssertionError("a fixed center is forbidden")
    admissible = tuple(
        center
        for center in range(SPACE_SIZE)
        if center not in fixed and center not in forbidden
    )
    holes = tuple(
        point
        for point in range(SPACE_SIZE)
        if all(
            DISTANCES[point][center] > RADIUS
            for center in fixed
        )
    )
    return representative, fixed, forbidden, admissible, holes


def count_block(point, coordinates):
    counts = Counter(WORDS[point][coordinate] for coordinate in coordinates)
    return "".join(str(counts[symbol]) for symbol in range(ALPHABET))


def certificate_key(point, representative, anchor_weight):
    third = WORDS[representative]
    if anchor_weight == 5:
        blocks = [
            count_block(
                point,
                [
                    coordinate
                    for coordinate in range(5)
                    if third[coordinate] == symbol
                ],
            )
            for symbol in range(ALPHABET)
        ]
        blocks.append("0" if WORDS[point][5] == 0 else "1")
        return "|".join(blocks)
    if anchor_weight == 6:
        return "|".join(
            count_block(
                point,
                [
                    coordinate
                    for coordinate in range(LENGTH)
                    if third[coordinate] == symbol
                ],
            )
            for symbol in (0, 2)
        )
    raise AssertionError("unsupported anchor weight")


def verify_certificate(certificate, target_centers):
    integer_fields = (
        "anchor_weight",
        "third_orbit",
        "expected_admissible_centers",
        "expected_holes",
        "expected_total_weight",
        "expected_max_capacity",
    )
    for field in integer_fields:
        if type(certificate.get(field)) is not int:
            raise AssertionError(f"{field} must be an integer")
    if type(target_centers) is not int:
        raise AssertionError("target center count must be an integer")
    if type(certificate.get("representative")) is not str:
        raise AssertionError("representative must be a string")

    anchor_weight = certificate["anchor_weight"]
    orbit_index = certificate["third_orbit"]
    (
        representative,
        fixed,
        _,
        admissible,
        holes,
    ) = branch_data(anchor_weight, orbit_index)
    representative_text = format_word(WORDS[representative])
    if representative_text != certificate["representative"]:
        raise AssertionError("third-center representative mismatch")
    if len(fixed) != 3:
        raise AssertionError("certificate branch must fix three centers")
    if len(admissible) != certificate["expected_admissible_centers"]:
        raise AssertionError("admissible-center count mismatch")
    if len(holes) != certificate["expected_holes"]:
        raise AssertionError("hole count mismatch")

    entries = {}
    expected_orbit_sizes = {}
    for entry in certificate["weights"]:
        key = entry["key"]
        if type(key) is not str:
            raise AssertionError("certificate orbit key must be a string")
        if key in entries:
            raise AssertionError("duplicate certificate orbit key")
        if type(entry.get("weight")) is not int or entry["weight"] <= 0:
            raise AssertionError("certificate weights must be positive")
        if (
            type(entry.get("orbit_size")) is not int
            or entry["orbit_size"] <= 0
        ):
            raise AssertionError(
                "certificate orbit sizes must be positive integers"
            )
        entries[key] = entry["weight"]
        expected_orbit_sizes[key] = entry["orbit_size"]

    ambient_by_key = defaultdict(list)
    for point in range(SPACE_SIZE):
        key = certificate_key(point, representative, anchor_weight)
        if key in entries:
            ambient_by_key[key].append(point)
    if set(ambient_by_key) != set(entries):
        raise AssertionError("certificate orbit key has no ambient points")
    hole_set = set(holes)
    for key, members in ambient_by_key.items():
        if len(members) != expected_orbit_sizes[key]:
            raise AssertionError("certificate orbit size mismatch")
        if not set(members) <= hole_set:
            raise AssertionError("positive-weight orbit contains a non-hole")

    point_weights = {
        point: entries.get(
            certificate_key(point, representative, anchor_weight),
            0,
        )
        for point in holes
    }
    total_weight = sum(point_weights.values())
    if total_weight != certificate["expected_total_weight"]:
        raise AssertionError("total certificate weight mismatch")

    capacities = {
        center: sum(
            point_weights[point]
            for point in holes
            if DISTANCES[point][center] <= RADIUS
        )
        for center in admissible
    }
    max_capacity = max(capacities.values(), default=0)
    if max_capacity != certificate["expected_max_capacity"]:
        raise AssertionError("maximum center capacity mismatch")

    remaining_centers = target_centers - len(fixed)
    upper_bound = remaining_centers * max_capacity
    if total_weight <= upper_bound:
        raise AssertionError("certificate does not prove a contradiction")
    return {
        "anchor_weight": anchor_weight,
        "third_orbit": orbit_index,
        "representative": representative_text,
        "admissible_centers": len(admissible),
        "holes": len(holes),
        "remaining_centers": remaining_centers,
        "total_weight": total_weight,
        "max_capacity": max_capacity,
        "upper_bound": upper_bound,
        "margin": total_weight - upper_bound,
        "max_capacity_centers": sum(
            capacity == max_capacity
            for capacity in capacities.values()
        ),
    }


def canonical_certificate_lines(document):
    lines = [
        f"schema {document['schema']}",
        f"target_centers {document['target_centers']}",
    ]
    for certificate in document["certificates"]:
        lines.append(
            "branch "
            f"{certificate['anchor_weight']} "
            f"{certificate['third_orbit']} "
            f"{certificate['representative']} "
            f"{certificate['expected_admissible_centers']} "
            f"{certificate['expected_holes']} "
            f"{certificate['expected_total_weight']} "
            f"{certificate['expected_max_capacity']}"
        )
        for entry in certificate["weights"]:
            lines.append(
                f"weight {entry['key']} "
                f"{entry['weight']} {entry['orbit_size']}"
            )
        lines.append("end")
    return tuple(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dump-certificate-data", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    path = root / "data" / "weighted_branch_certificates.json"
    document = json.loads(path.read_text())
    if type(document.get("schema")) is not int or document["schema"] != 1:
        raise AssertionError("unsupported certificate schema")
    target_centers = document["target_centers"]
    if type(target_centers) is not int or target_centers != 16:
        raise AssertionError("certificates are specialized to 16 centers")
    if args.dump_certificate_data:
        print("\n".join(canonical_certificate_lines(document)))
        return

    results = [
        verify_certificate(certificate, target_centers)
        for certificate in document["certificates"]
    ]
    if len(results) != 6:
        raise AssertionError("expected exactly six branch certificates")
    for result in results:
        print(
            "w{anchor_weight} orbit {third_orbit:02d} "
            "{representative}: |U|={admissible_centers} "
            "|H|={holes} W={total_weight} Q={max_capacity} "
            "13Q={upper_bound} margin={margin}".format(**result)
        )
    print("all weighted branch certificates verified")


if __name__ == "__main__":
    main()
