#!/usr/bin/env python3

import argparse
from collections import defaultdict
import hashlib
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import uuid

import ortools
from ortools.sat.python import cp_model


LENGTH = 6
ALPHABET = 3
SPACE_SIZE = ALPHABET ** LENGTH
TARGET_CENTERS = 16


def decode(value):
    digits = [0] * LENGTH
    for index in range(LENGTH - 1, -1, -1):
        digits[index] = value % ALPHABET
        value //= ALPHABET
    return tuple(digits)


WORDS = tuple(decode(value) for value in range(SPACE_SIZE))


def encode(digits):
    value = 0
    for digit in digits:
        value = ALPHABET * value + digit
    return value


def distance(left, right):
    return sum(a != b for a, b in zip(left, right))


def weight(word):
    return sum(digit != 0 for digit in word)


def format_word(word):
    return "".join(map(str, word))


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def hash_json(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True).encode()
    ).hexdigest()


def anchor_word(anchor_weight):
    return (1,) * anchor_weight + (0,) * (LENGTH - anchor_weight)


def build_distance_shells():
    result = []
    for word in WORDS:
        shells = [[] for _ in range(LENGTH + 1)]
        for other, other_word in enumerate(WORDS):
            shells[distance(word, other_word)].append(other)
        result.append(tuple(tuple(shell) for shell in shells))
    return tuple(result)


DISTANCE_SHELLS = build_distance_shells()
ZERO = encode((0,) * LENGTH)
SPHERE_SIZES = tuple(
    len(DISTANCE_SHELLS[ZERO][radius])
    for radius in range(LENGTH + 1)
)
SPHERE_CAPACITIES = tuple(
    tuple(
        sum(
            distance(WORDS[point], anchor_word(center_distance)) <= 2
            for point in DISTANCE_SHELLS[ZERO][radius]
        )
        for center_distance in range(LENGTH + 1)
    )
    for radius in range(LENGTH + 1)
)


def third_orbits(anchor_weight):
    anchor = anchor_word(anchor_weight)
    groups = defaultdict(list)
    for center, word in enumerate(WORDS):
        if word == (0,) * LENGTH or word == anchor:
            continue
        if weight(word) > anchor_weight:
            continue
        support = word[:anchor_weight]
        key = (
            support.count(0),
            support.count(1),
            support.count(2),
            sum(digit != 0 for digit in word[anchor_weight:]),
        )
        groups[key].append(center)
    return sorted(
        (
            min(members, key=lambda center: WORDS[center]),
            tuple(members),
        )
        for members in groups.values()
    )


def third_orbit_manifest(anchor_weight):
    orbits = third_orbits(anchor_weight)
    anchor = encode(anchor_word(anchor_weight))
    allowed = {
        center
        for center, word in enumerate(WORDS)
        if center not in {ZERO, anchor}
        and weight(word) <= anchor_weight
    }
    covered = set()
    entries = []
    for index, (representative, members) in enumerate(orbits):
        member_set = set(members)
        if not member_set or covered.intersection(member_set):
            raise RuntimeError("third-center orbits overlap or are empty")
        if representative != min(members):
            raise RuntimeError("third-center representative is not canonical")
        covered.update(member_set)
        entries.append(
            {
                "index": index,
                "representative": format_word(WORDS[representative]),
                "members": list(members),
                "members_sha256": hashlib.sha256(
                    json.dumps(list(members)).encode()
                ).hexdigest(),
            }
        )
    if covered != allowed:
        raise RuntimeError("third-center orbits do not cover the branch")
    return {
        "schema": 1,
        "weight": anchor_weight,
        "allowed_centers": len(allowed),
        "orbit_count": len(entries),
        "orbits": entries,
    }


def add_projection_five_constraints(model, variables):
    for omitted in range(LENGTH):
        coordinates = [
            coordinate
            for coordinate in range(LENGTH)
            if coordinate != omitted
        ]
        for pattern_value in range(ALPHABET ** 5):
            pattern = decode(pattern_value)[1:]
            shells = [[], [], []]
            for center, word in enumerate(WORDS):
                projected_distance = sum(
                    word[coordinate] != pattern[index]
                    for index, coordinate in enumerate(coordinates)
                )
                if projected_distance <= 2:
                    shells[projected_distance].append(variables[center])
            model.Add(
                3 * sum(shells[0])
                + 3 * sum(shells[1])
                + sum(shells[2])
                >= 3
            )


def add_projection_two_constraints(model, variables):
    for first in range(LENGTH):
        for second in range(first + 1, LENGTH):
            for first_symbol in range(ALPHABET):
                row = [
                    variables[center]
                    for center, word in enumerate(WORDS)
                    if word[first] == first_symbol
                ]
                for second_symbol in range(ALPHABET):
                    column = [
                        variables[center]
                        for center, word in enumerate(WORDS)
                        if word[second] == second_symbol
                    ]
                    cell = [
                        variables[center]
                        for center, word in enumerate(WORDS)
                        if word[first] == first_symbol
                        and word[second] == second_symbol
                    ]
                    model.Add(
                        2 * sum(cell) + sum(row) + sum(column) >= 9
                    )


def build_model(args):
    model = cp_model.CpModel()
    variables = [
        model.NewBoolVar(f"x_{format_word(word)}")
        for word in WORDS
    ]

    model.Add(sum(variables) == TARGET_CENTERS)
    zero = ZERO
    anchor = encode(anchor_word(args.weight))
    model.Add(variables[zero] == 1)
    model.Add(variables[anchor] == 1)
    for center, word in enumerate(WORDS):
        if weight(word) > args.weight:
            model.Add(variables[center] == 0)

    if args.third_orbit is not None:
        orbits = third_orbits(args.weight)
        if args.third_orbit < 0 or args.third_orbit >= len(orbits):
            raise ValueError(
                f"third orbit must be in 0..{len(orbits) - 1}"
            )
        representative, _ = orbits[args.third_orbit]
        model.Add(variables[representative] == 1)
        for _, members in orbits[:args.third_orbit]:
            for center in members:
                model.Add(variables[center] == 0)

    for point, point_word in enumerate(WORDS):
        covering = [
            variables[center]
            for shell_distance in range(3)
            for center in DISTANCE_SHELLS[point][shell_distance]
        ]
        model.Add(sum(covering) >= 1)

    for coordinate in range(LENGTH):
        for symbol in range(ALPHABET):
            symbol_class = [
                variables[center]
                for center, word in enumerate(WORDS)
                if word[coordinate] == symbol
            ]
            model.Add(sum(symbol_class) >= 3)
            model.Add(sum(symbol_class) <= 10)

    for point in range(SPACE_SIZE):
        shells = [
            [
                variables[center]
                for center in DISTANCE_SHELLS[point][d]
            ]
            for d in range(LENGTH + 1)
        ]
        for radius in range(1, LENGTH + 1):
            model.Add(
                sum(
                    SPHERE_CAPACITIES[radius][shell_distance]
                    * sum(shells[shell_distance])
                    for shell_distance in range(LENGTH + 1)
                    if SPHERE_CAPACITIES[radius][shell_distance]
                )
                >= SPHERE_SIZES[radius]
            )

    if args.two_projection_cuts:
        add_projection_two_constraints(model, variables)
    if args.five_projection_cuts:
        add_projection_five_constraints(model, variables)
    return model, variables


def model_sha256(model):
    return hashlib.sha256(
        model.Proto().SerializeToString(deterministic=True)
    ).hexdigest()


def model_identity(args, digest):
    identity = {
        "weight": args.weight,
        "third_orbit": args.third_orbit,
        "two_projection_cuts": args.two_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "model_sha256": digest,
    }
    if args.third_orbit is not None:
        manifest = third_orbit_manifest(args.weight)
        representative, members = third_orbits(args.weight)[
            args.third_orbit
        ]
        identity.update(
            {
                "orbit_representative": format_word(
                    WORDS[representative]
                ),
                "orbit_members_sha256": hashlib.sha256(
                    json.dumps(sorted(members)).encode()
                ).hexdigest(),
                "orbit_manifest_sha256": hash_json(manifest),
            }
        )
    return identity


def fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_text(path, contents):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary.open("w") as handle:
            handle.write(contents)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
        fsync_directory(path.parent)
    finally:
        temporary.unlink(missing_ok=True)


def verify_solution(root, selected, output):
    temporary = output.with_name(
        f"{output.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        with temporary.open("w") as handle:
            handle.write(
                "".join(
                    f"{format_word(WORDS[center])}\n"
                    for center in selected
                )
            )
            handle.flush()
            os.fsync(handle.fileno())
        completed = subprocess.run(
            [str(root / "build" / "verify_code"), str(temporary)],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        expected_lines = {
            "centers: 16",
            "distinct: yes",
            "holes: 0",
        }
        actual_lines = set(completed.stdout.splitlines())
        if (
            completed.returncode != 0
            or not expected_lines.issubset(actual_lines)
        ):
            raise RuntimeError(
                "witness verification failed"
            )
        temporary.replace(output)
        fsync_directory(output.parent)
    finally:
        temporary.unlink(missing_ok=True)


def write_result(root, path, result):
    if path is None:
        return
    if not path.is_absolute():
        path = root / path
    atomic_write_text(
        path,
        json.dumps(result, indent=2, sort_keys=True) + "\n",
    )


def solver_exit_code(status_name):
    if status_name in {"OPTIMAL", "FEASIBLE"}:
        return 0
    if status_name == "INFEASIBLE":
        return 20
    if status_name == "UNKNOWN":
        return 3
    return 4


def solver_classification(status_name):
    if status_name in {"OPTIMAL", "FEASIBLE"}:
        return "verified-witness-pending"
    if status_name == "INFEASIBLE":
        return "solver-only-infeasible"
    if status_name == "UNKNOWN":
        return "unresolved"
    return "operational-error"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=int, required=True, choices=(4, 5, 6))
    parser.add_argument("--third-orbit", type=int)
    parser.add_argument("--seconds", type=float, default=300)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument(
        "--two-projection-cuts",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--five-projection-cuts", action="store_true")
    parser.add_argument("--log-search", action="store_true")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("research-results/cp-sat/solution.txt"),
    )
    parser.add_argument("--result-json", type=Path)
    parser.add_argument("--campaign-fingerprint")
    parser.add_argument(
        "--list-third-orbits-json",
        action="store_true",
    )
    parser.add_argument(
        "--model-metadata-json",
        action="store_true",
    )
    args = parser.parse_args()
    if args.seconds <= 0 or args.workers <= 0:
        raise SystemExit("seconds and workers must be positive")
    if args.list_third_orbits_json and args.model_metadata_json:
        raise SystemExit(
            "orbit listing and model metadata modes are mutually exclusive"
        )

    root = Path(__file__).resolve().parent.parent
    if args.list_third_orbits_json:
        print(json.dumps(third_orbit_manifest(args.weight), sort_keys=True))
        return 0

    model, variables = build_model(args)
    validation_error = model.Validate()
    if validation_error:
        raise RuntimeError(f"invalid CP-SAT model: {validation_error}")
    identity = model_identity(args, model_sha256(model))
    if args.model_metadata_json:
        print(
            json.dumps(
                {
                    "schema": 1,
                    **identity,
                    "ortools_version": ortools.__version__,
                },
                sort_keys=True,
            )
        )
        return 0
    print(model.ModelStats(), flush=True)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = args.seconds
    solver.parameters.num_search_workers = args.workers
    solver.parameters.random_seed = args.seed
    solver.parameters.log_search_progress = args.log_search
    solver.parameters.symmetry_level = 3

    status = solver.Solve(model)
    status_name = solver.StatusName(status)
    exit_code = solver_exit_code(status_name)
    print(f"status: {status_name}")
    print(f"wall time: {solver.WallTime():.6f}")
    print(f"branches: {solver.NumBranches()}")
    print(f"conflicts: {solver.NumConflicts()}")
    result = {
        "schema": 2,
        "status": status_name,
        "classification": solver_classification(status_name),
        "exit_code": exit_code,
        "weight": args.weight,
        "third_orbit": args.third_orbit,
        "time_limit_seconds": args.seconds,
        "workers": args.workers,
        "seed": args.seed,
        "two_projection_cuts": args.two_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "wall_time_seconds": solver.WallTime(),
        "branches": solver.NumBranches(),
        "conflicts": solver.NumConflicts(),
        "selected_centers": [],
        "witness_verified": False,
        "campaign_fingerprint": args.campaign_fingerprint,
        **identity,
        "script_sha256": hash_file(Path(__file__).resolve()),
        "verifier_sha256": hash_file(root / "build" / "verify_code"),
        "ortools_version": ortools.__version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "command": [
            (
                str(Path(sys.executable).resolve().relative_to(root))
                if Path(sys.executable).resolve().is_relative_to(root)
                else str(Path(sys.executable).resolve())
            ),
            *sys.argv,
        ],
    }
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        selected = [
            center
            for center, variable in enumerate(variables)
            if solver.Value(variable)
        ]
        if len(selected) != TARGET_CENTERS:
            raise RuntimeError("CP-SAT returned the wrong center count")
        output = args.output
        if not output.is_absolute():
            output = root / output
        output.parent.mkdir(parents=True, exist_ok=True)
        verify_solution(root, selected, output)
        result["selected_centers"] = [
            format_word(WORDS[center]) for center in selected
        ]
        result["witness_verified"] = True
        result["classification"] = "verified-witness"
        result["witness_sha256"] = hash_file(output)
        try:
            result["witness_path"] = str(output.relative_to(root))
        except ValueError:
            result["witness_path"] = str(output)
        write_result(root, args.result_json, result)
        return exit_code
    if exit_code == 4:
        result["error"] = f"unexpected solver status: {status_name}"
    write_result(root, args.result_json, result)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
