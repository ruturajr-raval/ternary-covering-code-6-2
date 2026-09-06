#!/usr/bin/env python3

import argparse
import concurrent.futures
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
from collections import Counter, deque
from pathlib import Path
import subprocess
import sys
import threading
import time
import uuid


RESULT_SCHEMA = 7
SPACE_SIZE = 729
TARGET_CENTERS = 16
FIXED_PREFIX_CENTERS = 2
MAX_ORBIT_PATH = TARGET_CENTERS - FIXED_PREFIX_CENTERS


def parse_path(text):
    if not text:
        return ()
    path = tuple(int(part) for part in text.split(","))
    if any(index < 0 for index in path):
        raise ValueError("orbit-path indices must be nonnegative")
    return path


def format_path(path):
    return "root" if not path else "_".join(str(value) for value in path)


def command_path(root, path):
    candidate = Path(path)
    try:
        relative = candidate.resolve().relative_to(root.resolve())
    except ValueError:
        return str(candidate)
    text = str(relative)
    return text if "/" in text else f"./{text}"


def generator_command(
    generator,
    weight,
    path,
    projection_cuts,
    four_projection_cuts,
    five_projection_cuts,
    antipodal_cuts,
    radial_sphere_cuts,
):
    command = [
        str(generator),
        "--centers",
        "16",
        "--anchor-weight",
        str(weight),
    ]
    if path:
        command.extend(["--orbit-path", ",".join(map(str, path))])
    if projection_cuts:
        command.append("--projection-cuts")
    if four_projection_cuts:
        command.append("--four-projection-cuts")
    if five_projection_cuts:
        command.append("--five-projection-cuts")
    if antipodal_cuts:
        command.append("--antipodal-cuts")
    if radial_sphere_cuts:
        command.append("--radial-sphere-cuts")
    return command


def list_next_orbits(root, generator, weight, path, timeout=300):
    command = [
        command_path(root, generator),
        "--anchor-weight",
        str(weight),
    ]
    if path:
        command.extend(["--orbit-path", ",".join(map(str, path))])
    command.append("--list-next-orbits")
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=root,
    )
    result = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        expected_index = len(result)
        match = re.fullmatch(
            r"(\d+) ([012]{6}) orbit_size=(\d+)",
            line.strip(),
        )
        if match is None:
            raise ValueError(f"invalid orbit listing line: {line}")
        index, representative, orbit_size = match.groups()
        if int(index) != expected_index:
            raise ValueError("orbit listing indices are not consecutive")
        result.append(
            {
                "index": int(index),
                "representative": representative,
                "orbit_size": int(orbit_size),
            }
        )
    return result


def hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify_log(text):
    statuses = re.findall(
        r"^[sc] (SATISFIABLE|UNSATISFIABLE|UNKNOWN)$",
        text,
        flags=re.MULTILINE,
    )
    if len(statuses) != 1:
        return "ERROR"
    return {
        "SATISFIABLE": "SAT",
        "UNSATISFIABLE": "UNSAT",
        "UNKNOWN": "UNKNOWN",
    }[statuses[0]]


def solver_result_is_consistent(outcome, exit_code):
    expected = {
        "SAT": 10,
        "UNSAT": 20,
        "UNKNOWN": 0,
    }
    return outcome in expected and exit_code == expected[outcome]


def format_center(center):
    digits = []
    value = center
    for _ in range(6):
        digits.append(str(value % 3))
        value //= 3
    return "".join(reversed(digits))


def selected_centers_from_model(text):
    assignments = {}
    for line in text.splitlines():
        if not line.startswith("v "):
            continue
        for token in line.split()[1:]:
            literal = int(token)
            if literal == 0:
                continue
            variable = abs(literal)
            if variable > SPACE_SIZE:
                continue
            value = literal > 0
            if variable in assignments and assignments[variable] != value:
                raise ValueError(
                    f"conflicting model values for variable {variable}"
                )
            assignments[variable] = value

    if len(assignments) != SPACE_SIZE:
        raise ValueError(
            "SAT model does not assign every center-selection variable"
        )
    return sorted(
        variable - 1
        for variable, selected in assignments.items()
        if selected
    )


def verify_sat_model(args, node_dir, log_text):
    centers = selected_centers_from_model(log_text)
    if len(centers) != TARGET_CENTERS:
        raise ValueError(
            f"SAT model selects {len(centers)} centers, expected "
            f"{TARGET_CENTERS}"
        )

    solution_path = node_dir / "solution.txt"
    solution_path.write_text(
        "".join(f"{format_center(center)}\n" for center in centers)
    )
    completed = subprocess.run(
        [str(args.verifier), str(solution_path)],
        cwd=args.root,
        capture_output=True,
        text=True,
    )
    verification_text = completed.stdout + completed.stderr
    (node_dir / "verification.txt").write_text(verification_text)
    if completed.returncode != 0:
        raise ValueError("decoded SAT model fails the configured verifier")
    required_lines = {
        f"centers: {TARGET_CENTERS}",
        "distinct: yes",
        "holes: 0",
    }
    if not required_lines.issubset(set(verification_text.splitlines())):
        raise ValueError("verifier output is missing required success fields")
    return centers


def valid_next_orbits(result):
    orbits = result.get("next_orbits")
    if (
        not isinstance(orbits, list)
        or result.get("next_count") != len(orbits)
    ):
        return False
    return all(
        entry.get("index") == index
        and re.fullmatch(
            r"[012]{6}", str(entry.get("representative", ""))
        )
        is not None
        and isinstance(entry.get("orbit_size"), int)
        and entry["orbit_size"] > 0
        for index, entry in enumerate(orbits)
    )


def verify_cached_sat_witness(args, node_dir, result):
    solution_path = node_dir / "solution.txt"
    verification_path = node_dir / "verification.txt"
    if (
        not solution_path.exists()
        or not verification_path.exists()
        or result.get("solution_sha256") != hash_file(solution_path)
        or result.get("verification_sha256")
        != hash_file(verification_path)
    ):
        return False
    words = [
        line.strip()
        for line in solution_path.read_text().splitlines()
        if line.strip()
    ]
    if (
        len(words) != TARGET_CENTERS
        or len(set(words)) != TARGET_CENTERS
        or any(re.fullmatch(r"[012]{6}", word) is None for word in words)
    ):
        return False
    selected = sorted(int(word, 3) for word in words)
    if selected != result.get("selected_centers"):
        return False
    completed = subprocess.run(
        [str(args.verifier), str(solution_path)],
        cwd=args.root,
        capture_output=True,
        text=True,
    )
    verification_text = completed.stdout + completed.stderr
    required_lines = {
        f"centers: {TARGET_CENTERS}",
        "distinct: yes",
        "holes: 0",
    }
    return (
        completed.returncode == 0
        and required_lines.issubset(
            set(verification_text.splitlines())
        )
    )


def write_json(path, value):
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    with temporary.open("w") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def terminate_process(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    process.wait()


def run_process(
    command,
    stdout_path,
    timeout,
    cancel_event,
    stderr_path=None,
    cwd=None,
):
    started = time.monotonic()
    process = None
    with stdout_path.open("wb") as stdout:
        if stderr_path is None:
            stderr = subprocess.STDOUT
            stderr_handle = None
        else:
            stderr_handle = stderr_path.open("wb")
            stderr = stderr_handle
        try:
            process = subprocess.Popen(
                command,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                cwd=cwd,
            )
            deadline = started + timeout
            stop_reason = None
            while process.poll() is None:
                if cancel_event.is_set():
                    stop_reason = "cancelled"
                    terminate_process(process)
                    break
                if time.monotonic() >= deadline:
                    stop_reason = "timeout"
                    terminate_process(process)
                    break
                time.sleep(0.1)
            exit_code = process.wait()
            stdout.flush()
            os.fsync(stdout.fileno())
            if stderr_handle is not None:
                stderr_handle.flush()
                os.fsync(stderr_handle.fileno())
            return exit_code, time.monotonic() - started, stop_reason
        finally:
            if process is not None and process.poll() is None:
                terminate_process(process)
            if stderr_handle is not None:
                stderr_handle.close()


def acquire_campaign_lock(output):
    lock_path = output / ".campaign.lock"
    handle = lock_path.open("a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        handle.close()
        raise RuntimeError(
            f"another coordinator is active for {output}"
        ) from error
    handle.seek(0)
    handle.truncate()
    handle.write(f"{os.getpid()}\n")
    handle.flush()
    os.fsync(handle.fileno())
    return handle


def acquire_generation_lock(args):
    handle = args.generation_lock_path.open("a+")
    while True:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return handle
        except BlockingIOError:
            if args.cancel_event.is_set():
                handle.close()
                raise InterruptedError("campaign cancellation requested")
            time.sleep(0.1)


def clean_stale_temporaries(output):
    for path in output.rglob("*.tmp"):
        path.unlink(missing_ok=True)


def campaign_fingerprint(args):
    payload = {
        "schema": RESULT_SCHEMA,
        "weight": args.weight,
        "projection_cuts": args.projection_cuts,
        "four_projection_cuts": args.four_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "antipodal_cuts": args.antipodal_cuts,
        "radial_sphere_cuts": args.radial_sphere_cuts,
        "generator_sha256": args.generator_sha256,
        "solver_sha256": args.solver_sha256,
        "verifier_sha256": args.verifier_sha256,
        "coordinator_sha256": args.coordinator_sha256,
        "git_commit": args.git_commit,
        "git_tracked_dirty": args.git_tracked_dirty,
        "target_centers": TARGET_CENTERS,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()


def git_provenance(root):
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        status = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None, None
    return commit, bool(status.strip())


def result_is_reusable(args, path, result, honor_rerun=True):
    if (
        (honor_rerun and args.rerun)
        or result.get("schema") != RESULT_SCHEMA
    ):
        return False
    expected = {
        "weight": args.weight,
        "path": list(path),
        "projection_cuts": args.projection_cuts,
        "four_projection_cuts": args.four_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "antipodal_cuts": args.antipodal_cuts,
        "radial_sphere_cuts": args.radial_sphere_cuts,
        "campaign_fingerprint": args.campaign_fingerprint,
    }
    if any(result.get(key) != value for key, value in expected.items()):
        return False
    expected_components = {
        "coordinator_sha256": args.coordinator_sha256,
        "generator_sha256": args.generator_sha256,
        "solver_sha256": args.solver_sha256,
        "verifier_sha256": args.verifier_sha256,
        "git_commit": args.git_commit,
        "git_tracked_dirty": args.git_tracked_dirty,
    }
    if any(
        result.get(key) != value
        for key, value in expected_components.items()
    ):
        return False
    node_dir = args.output / format_path(path)
    cnf_path = node_dir / "case.cnf"
    expected_generator_command = generator_command(
        command_path(args.root, args.generator),
        args.weight,
        path,
        args.projection_cuts,
        args.four_projection_cuts,
        args.five_projection_cuts,
        args.antipodal_cuts,
        args.radial_sphere_cuts,
    )
    if result.get("generator_command") != expected_generator_command:
        return False
    recorded_seconds = result.get("time_limit_seconds")
    if not isinstance(recorded_seconds, int) or recorded_seconds <= 0:
        return False
    expected_solver_command = [
        command_path(args.root, args.solver),
        "-t",
        str(recorded_seconds),
        str(cnf_path.relative_to(args.root)),
    ]
    if result.get("solver_command") != expected_solver_command:
        return False
    log_path = node_dir / "solve.log"
    if (
        not log_path.exists()
        or result.get("solve_log_sha256") != hash_file(log_path)
    ):
        return False
    solver_outcome = classify_log(log_path.read_text(errors="replace"))
    if (
        solver_outcome != result.get("solver_outcome")
        or not solver_result_is_consistent(
            solver_outcome, result.get("exit_code")
        )
    ):
        return False
    if not valid_next_orbits(result):
        return False
    outcome = result.get("outcome")
    if outcome in {"CANCELLED", "ERROR"}:
        return False
    if outcome == "UNKNOWN":
        return result.get("time_limit_seconds", 0) >= args.seconds
    if outcome == "SAT_VERIFIED":
        expected_verifier_command = [
            command_path(args.root, args.verifier),
            str((node_dir / "solution.txt").relative_to(args.root)),
        ]
        return (
            result.get("witness_verified") is True
            and result.get("verifier_command")
            == expected_verifier_command
            and cnf_path.exists()
            and result.get("cnf_sha256") == hash_file(cnf_path)
            and verify_cached_sat_witness(args, node_dir, result)
        )
    return outcome in {"SOLVER_UNSAT", "UNSAT_VERIFIED"}


def cached_result(args, path):
    result_path = args.output / format_path(path) / "result.json"
    if not result_path.exists():
        return None
    try:
        result = json.loads(result_path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return result if result_is_reusable(args, path, result) else None


def can_have_remaining_center(path):
    return len(path) < MAX_ORBIT_PATH


def initial_result(args, path):
    return {
        "schema": RESULT_SCHEMA,
        "campaign_fingerprint": args.campaign_fingerprint,
        "weight": args.weight,
        "path": list(path),
        "depth": len(path),
        "outcome": "ERROR",
        "solver_outcome": "ERROR",
        "exit_code": None,
        "generation_exit_code": None,
        "generation_seconds": None,
        "elapsed_seconds": None,
        "time_limit_seconds": args.seconds,
        "cnf_sha256": None,
        "cnf_size": None,
        "solve_log_sha256": None,
        "solution_sha256": None,
        "verification_sha256": None,
        "next_count": 0,
        "next_orbits": [],
        "projection_cuts": args.projection_cuts,
        "four_projection_cuts": args.four_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "antipodal_cuts": args.antipodal_cuts,
        "radial_sphere_cuts": args.radial_sphere_cuts,
        "coordinator": command_path(args.root, args.coordinator),
        "coordinator_sha256": args.coordinator_sha256,
        "git_commit": args.git_commit,
        "git_tracked_dirty": args.git_tracked_dirty,
        "solver": command_path(args.root, args.solver),
        "solver_sha256": args.solver_sha256,
        "generator": command_path(args.root, args.generator),
        "generator_sha256": args.generator_sha256,
        "verifier": command_path(args.root, args.verifier),
        "verifier_sha256": args.verifier_sha256,
        "witness_verified": False,
        "selected_centers": [],
        "proof_status": "none",
        "failed_stage": None,
        "error": None,
        "generator_command": [],
        "solver_command": [],
        "verifier_command": [],
    }


def run_node(args, path):
    label = format_path(path)
    node_dir = args.output / label
    node_dir.mkdir(parents=True, exist_ok=True)
    result_path = node_dir / "result.json"
    reusable = cached_result(args, path)
    if reusable is not None:
        return reusable

    result = initial_result(args, path)
    cnf_path = node_dir / "case.cnf"
    cnf_path.unlink(missing_ok=True)
    token = f"{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}"
    temporary_cnf_path = node_dir / f"case.cnf.{token}.tmp"
    generation_stderr_path = node_dir / f"generate.stderr.{token}.tmp"
    log_path = node_dir / "solve.log"
    temporary_log_path = node_dir / f"solve.log.{token}.tmp"
    command = generator_command(
        command_path(args.root, args.generator),
        args.weight,
        path,
        args.projection_cuts,
        args.four_projection_cuts,
        args.five_projection_cuts,
        args.antipodal_cuts,
        args.radial_sphere_cuts,
    )
    result["generator_command"] = command
    stage = "generation"
    try:
        with args.storage_lock:
            generation_lock = acquire_generation_lock(args)
            try:
                free_bytes = shutil.disk_usage(args.root).free
                if free_bytes < args.minimum_free_bytes:
                    raise OSError(
                        "free disk space is below the configured admission "
                        "floor"
                    )
                generation_exit_code, generation_seconds, stop_reason = (
                    run_process(
                        command,
                        temporary_cnf_path,
                        args.generation_seconds,
                        args.cancel_event,
                        generation_stderr_path,
                        args.root,
                    )
                )
                result["generation_exit_code"] = generation_exit_code
                result["generation_seconds"] = round(generation_seconds, 6)
                if stop_reason == "cancelled":
                    result["outcome"] = "CANCELLED"
                    result["failed_stage"] = stage
                    result["error"] = "campaign cancellation requested"
                    write_json(result_path, result)
                    return result
                if stop_reason == "timeout":
                    raise TimeoutError(
                        "CNF generation exceeded its time limit"
                    )
                if generation_exit_code != 0:
                    details = generation_stderr_path.read_text(
                        errors="replace"
                    )[-2000:]
                    raise RuntimeError(
                        f"CNF generator exited {generation_exit_code}: "
                        f"{details}"
                    )
                temporary_cnf_path.replace(cnf_path)
                result["cnf_size"] = cnf_path.stat().st_size
                if (
                    shutil.disk_usage(args.root).free
                    < args.minimum_free_bytes
                ):
                    cnf_path.unlink(missing_ok=True)
                    raise OSError(
                        "generated CNF crossed the configured free-space "
                        "floor"
                    )
            finally:
                fcntl.flock(generation_lock.fileno(), fcntl.LOCK_UN)
                generation_lock.close()

        stage = "hashing"
        result["cnf_sha256"] = hash_file(cnf_path)

        stage = "solving"
        solver_command = [
            command_path(args.root, args.solver),
            "-t",
            str(args.seconds),
            str(cnf_path.relative_to(args.root)),
        ]
        result["solver_command"] = solver_command
        exit_code, elapsed, stop_reason = run_process(
            solver_command,
            temporary_log_path,
            args.seconds + 90,
            args.cancel_event,
            cwd=args.root,
        )
        temporary_log_path.replace(log_path)
        result["solve_log_sha256"] = hash_file(log_path)
        result["exit_code"] = exit_code
        result["elapsed_seconds"] = round(elapsed, 6)
        if stop_reason == "cancelled":
            result["outcome"] = "CANCELLED"
            result["failed_stage"] = stage
            result["error"] = "campaign cancellation requested"
        elif stop_reason == "timeout":
            result["outcome"] = "ERROR"
            result["failed_stage"] = stage
            result["error"] = (
                "solver exceeded the wall-clock limit plus shutdown grace"
            )
        else:
            log_text = log_path.read_text(errors="replace")
            solver_outcome = classify_log(log_text)
            result["solver_outcome"] = solver_outcome
            if not solver_result_is_consistent(solver_outcome, exit_code):
                result["outcome"] = "ERROR"
                result["failed_stage"] = stage
                result["error"] = (
                    f"inconsistent solver result {solver_outcome} with exit "
                    f"code {exit_code}"
                )
            elif solver_outcome == "UNSAT":
                result["outcome"] = "SOLVER_UNSAT"
                result["proof_status"] = "not-generated"
            elif solver_outcome == "UNKNOWN":
                result["outcome"] = "UNKNOWN"
            else:
                stage = "witness_verification"
                result["verifier_command"] = [
                    command_path(args.root, args.verifier),
                    str((node_dir / "solution.txt").relative_to(args.root)),
                ]
                selected_centers = verify_sat_model(
                    args, node_dir, log_text
                )
                result["outcome"] = "SAT_VERIFIED"
                result["witness_verified"] = True
                result["selected_centers"] = selected_centers
                result["proof_status"] = "direct-witness-verification"
                result["solution_sha256"] = hash_file(
                    node_dir / "solution.txt"
                )
                result["verification_sha256"] = hash_file(
                    node_dir / "verification.txt"
                )

        if (
            result["outcome"] == "UNKNOWN"
            and can_have_remaining_center(path)
        ):
            stage = "orbit_enumeration"
            result["next_orbits"] = list_next_orbits(
                args.root,
                args.generator,
                args.weight,
                path,
                timeout=args.generation_seconds,
            )
            result["next_count"] = len(result["next_orbits"])
    except Exception as exception:
        result["outcome"] = "ERROR"
        result["failed_stage"] = stage
        result["error"] = f"{type(exception).__name__}: {exception}"
    finally:
        temporary_cnf_path.unlink(missing_ok=True)
        temporary_log_path.unlink(missing_ok=True)
        generation_stderr_path.unlink(missing_ok=True)

    write_json(result_path, result)
    if (
        result["outcome"] in {"CANCELLED", "UNKNOWN", "SOLVER_UNSAT"}
        and not args.keep_cnf
    ):
        cnf_path.unlink(missing_ok=True)
    return result


def audit_result_records(args):
    audit = Counter()
    for result_path in args.output.glob("*/result.json"):
        try:
            result = json.loads(result_path.read_text())
            path = tuple(result["path"])
        except (json.JSONDecodeError, OSError):
            audit["corrupt"] += 1
            continue
        except (KeyError, TypeError, ValueError):
            audit["corrupt"] += 1
            continue
        if result_is_reusable(
            args, path, result, honor_rerun=False
        ):
            audit["compatible"] += 1
        else:
            audit["incompatible"] += 1
    return dict(sorted(audit.items()))


def reduce_tree(path, results, max_depth):
    result = results.get(path)
    if result is None:
        return "DEFERRED"
    outcome = result["outcome"]
    if outcome == "SAT_VERIFIED":
        return "SAT_VERIFIED"
    if outcome == "UNSAT_VERIFIED":
        return "UNSAT_VERIFIED"
    if outcome == "SOLVER_UNSAT":
        return "SOLVER_CLOSED"
    if outcome == "ERROR":
        return "ERROR"
    if outcome == "CANCELLED":
        return "DEFERRED"
    if outcome != "UNKNOWN":
        return "ERROR"
    if (
        len(path) >= max_depth
        or not can_have_remaining_center(path)
        or result["next_count"] <= 0
    ):
        return "OPEN"

    child_states = [
        reduce_tree(path + (child,), results, max_depth)
        for child in range(result["next_count"])
    ]
    if "SAT_VERIFIED" in child_states:
        return "SAT_VERIFIED"
    if "ERROR" in child_states:
        return "ERROR"
    if "OPEN" in child_states:
        return "OPEN"
    if "DEFERRED" in child_states:
        return "DEFERRED"
    if all(state == "UNSAT_VERIFIED" for state in child_states):
        return "UNSAT_VERIFIED"
    if all(
        state in {"SOLVER_CLOSED", "UNSAT_VERIFIED"}
        for state in child_states
    ):
        return "SOLVER_CLOSED"
    return "ERROR"


def write_summary(args, root_path, results, run):
    values = list(results.values())
    outcomes = Counter(result["outcome"] for result in values)
    depths = Counter(
        (result["depth"], result["outcome"]) for result in values
    )
    root_state = reduce_tree(root_path, results, args.max_depth)
    run = dict(run)
    run["root_state"] = root_state
    run["certified_complete"] = root_state in {
        "SAT_VERIFIED",
        "UNSAT_VERIFIED",
    }
    run["solver_complete"] = root_state in {
        "SAT_VERIFIED",
        "SOLVER_CLOSED",
        "UNSAT_VERIFIED",
    }
    summary = {
        "schema": RESULT_SCHEMA,
        "campaign_fingerprint": args.campaign_fingerprint,
        "git_commit": args.git_commit,
        "git_tracked_dirty": args.git_tracked_dirty,
        "weight": args.weight,
        "root_path": list(root_path),
        "projection_cuts": args.projection_cuts,
        "four_projection_cuts": args.four_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "antipodal_cuts": args.antipodal_cuts,
        "radial_sphere_cuts": args.radial_sphere_cuts,
        "time_limit_seconds": args.seconds,
        "max_depth": args.max_depth,
        "nodes": len(values),
        "outcomes": dict(sorted(outcomes.items())),
        "depth_outcomes": {
            f"{depth}:{outcome}": count
            for (depth, outcome), count in sorted(depths.items())
        },
        "artifacts": audit_result_records(args),
        "run": run,
    }
    write_json(args.output / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return root_state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=int, required=True, choices=(4, 5, 6))
    parser.add_argument("--seconds", type=int, default=30)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--max-depth", type=int, default=8)
    parser.add_argument("--max-nodes", type=int, default=2000)
    parser.add_argument("--root-path", default="")
    parser.add_argument("--projection-cuts", action="store_true")
    parser.add_argument("--four-projection-cuts", action="store_true")
    parser.add_argument("--five-projection-cuts", action="store_true")
    parser.add_argument("--antipodal-cuts", action="store_true")
    parser.add_argument("--radial-sphere-cuts", action="store_true")
    parser.add_argument("--keep-cnf", action="store_true")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--generation-seconds", type=int, default=300)
    parser.add_argument("--minimum-free-gb", type=float, default=2.0)
    parsed = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    parsed.root = root
    parsed.coordinator = Path(__file__).resolve()
    parsed.generator = root / "build" / "generate_cnf"
    parsed.solver = root / ".tools" / "cadical" / "build" / "cadical"
    parsed.verifier = root / "build" / "verify_code"
    try:
        root_path = parse_path(parsed.root_path)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    if len(root_path) > MAX_ORBIT_PATH:
        raise SystemExit(
            f"root path fixes more than {TARGET_CENTERS} centers"
        )
    if parsed.max_depth < len(root_path):
        raise SystemExit("max depth is shallower than the root path")
    enabled_cuts = []
    if parsed.projection_cuts:
        enabled_cuts.append("p2")
    if parsed.four_projection_cuts:
        enabled_cuts.append("p4")
    if parsed.five_projection_cuts:
        enabled_cuts.append("p5")
    if parsed.antipodal_cuts:
        enabled_cuts.append("anti")
    if parsed.radial_sphere_cuts:
        enabled_cuts.append("radial")
    suffix = "_".join(enabled_cuts) if enabled_cuts else "base"
    parsed.output = (
        root
        / "research-results"
        / "recursive-cubes"
        / f"w{parsed.weight}_{format_path(root_path)}_{suffix}"
    )
    parsed.output.mkdir(parents=True, exist_ok=True)

    for executable in (parsed.generator, parsed.solver, parsed.verifier):
        if not os.access(executable, os.X_OK):
            raise SystemExit(f"missing executable: {executable}")
    if parsed.seconds <= 0 or parsed.jobs <= 0:
        raise SystemExit("seconds and jobs must be positive")
    if parsed.max_nodes <= 0:
        raise SystemExit("max nodes must be positive")
    if parsed.generation_seconds <= 0:
        raise SystemExit("generation seconds must be positive")
    if parsed.minimum_free_gb < 0:
        raise SystemExit("minimum free space must be nonnegative")

    parsed.generator_sha256 = hash_file(parsed.generator)
    parsed.solver_sha256 = hash_file(parsed.solver)
    parsed.verifier_sha256 = hash_file(parsed.verifier)
    parsed.coordinator_sha256 = hash_file(parsed.coordinator)
    parsed.git_commit, parsed.git_tracked_dirty = git_provenance(root)
    parsed.campaign_fingerprint = campaign_fingerprint(parsed)
    parsed.minimum_free_bytes = int(
        parsed.minimum_free_gb * 1024 * 1024 * 1024
    )
    parsed.cancel_event = threading.Event()
    parsed.storage_lock = threading.Lock()
    parsed.generation_lock_path = (
        root / "research-results" / ".generation.lock"
    )

    try:
        campaign_lock = acquire_campaign_lock(parsed.output)
    except RuntimeError as error:
        raise SystemExit(str(error)) from error

    try:
        clean_stale_temporaries(parsed.output)
        queue = deque([root_path])
        seen = {root_path}
        results = {}
        submitted = 0
        cached = 0
        sat_result = None
        errors = 0
        interrupted = False

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=parsed.jobs
        ) as executor:
            try:
                running = {}
                while queue or running:
                    while queue and len(running) < parsed.jobs:
                        path = queue.popleft()
                        reusable = cached_result(parsed, path)
                        if reusable is not None:
                            cached += 1
                            result = reusable
                            results[path] = result
                            print(
                                f"{format_path(path)} {result['outcome']} "
                                f"cached children={result['next_count']}",
                                flush=True,
                            )
                            if result["outcome"] == "SAT_VERIFIED":
                                sat_result = result
                                parsed.cancel_event.set()
                                queue.clear()
                                break
                            if result["outcome"] == "ERROR":
                                errors += 1
                            if (
                                result["outcome"] == "UNKNOWN"
                                and result["next_count"] > 0
                                and len(path) < parsed.max_depth
                                and can_have_remaining_center(path)
                            ):
                                for child in range(
                                    result["next_count"]
                                ):
                                    child_path = path + (child,)
                                    if child_path not in seen:
                                        seen.add(child_path)
                                        queue.append(child_path)
                            continue

                        if submitted >= parsed.max_nodes:
                            queue.appendleft(path)
                            break
                        future = executor.submit(run_node, parsed, path)
                        running[future] = path
                        submitted += 1

                    if sat_result is not None:
                        for pending in running:
                            pending.cancel()
                        break
                    if not running:
                        break
                    done, _ = concurrent.futures.wait(
                        running,
                        return_when=concurrent.futures.FIRST_COMPLETED,
                    )
                    for future in done:
                        path = running.pop(future)
                        try:
                            result = future.result()
                        except Exception as error:
                            print(
                                f"{format_path(path)} ERROR {error}",
                                file=sys.stderr,
                                flush=True,
                            )
                            errors += 1
                            continue

                        results[path] = result
                        elapsed = result["elapsed_seconds"]
                        elapsed_text = (
                            "n/a"
                            if elapsed is None
                            else f"{elapsed:.2f}s"
                        )
                        print(
                            f"{format_path(path)} {result['outcome']} "
                            f"{elapsed_text} "
                            f"children={result['next_count']}",
                            flush=True,
                        )
                        if result["outcome"] == "SAT_VERIFIED":
                            sat_result = result
                            parsed.cancel_event.set()
                            queue.clear()
                            for pending in running:
                                pending.cancel()
                            break
                        if result["outcome"] == "ERROR":
                            errors += 1
                        if (
                            result["outcome"] == "UNKNOWN"
                            and result["next_count"] > 0
                            and len(path) < parsed.max_depth
                            and can_have_remaining_center(path)
                        ):
                            for child in range(result["next_count"]):
                                child_path = path + (child,)
                                if child_path not in seen:
                                    seen.add(child_path)
                                    queue.append(child_path)
                    if sat_result is not None:
                        break
            except KeyboardInterrupt:
                interrupted = True
                parsed.cancel_event.set()
                for pending in running:
                    pending.cancel()

        root_state = write_summary(
            parsed,
            root_path,
            results,
            {
                "cached_nodes": cached,
                "deferred_frontier_nodes": len(queue),
                "errors": errors,
                "interrupted": interrupted,
                "new_nodes": submitted,
                "sat_found": sat_result is not None,
            },
        )
        if interrupted:
            return 130
        if root_state == "SAT_VERIFIED":
            return 10
        if errors or root_state == "ERROR":
            return 2
        if root_state in {"SOLVER_CLOSED", "UNSAT_VERIFIED"}:
            return 0
        return 3
    finally:
        fcntl.flock(campaign_lock.fileno(), fcntl.LOCK_UN)
        campaign_lock.close()


if __name__ == "__main__":
    raise SystemExit(main())
