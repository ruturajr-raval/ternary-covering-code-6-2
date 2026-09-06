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


RESULT_SCHEMA = 2
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


def generator_command(generator, weight, path, projection_cuts):
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
    return command


def list_next_orbits(generator, weight, path, timeout=300):
    command = [
        str(generator),
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
    )
    return len([line for line in completed.stdout.splitlines() if line.strip()])


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
        capture_output=True,
        text=True,
    )
    verification_text = completed.stdout + completed.stderr
    (node_dir / "verification.txt").write_text(verification_text)
    if completed.returncode != 0:
        raise ValueError("decoded SAT model fails the independent verifier")
    required_lines = {
        f"centers: {TARGET_CENTERS}",
        "distinct: yes",
        "holes: 0",
    }
    if not required_lines.issubset(set(verification_text.splitlines())):
        raise ValueError("verifier output is missing required success fields")
    return centers


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
        "generator_sha256": args.generator_sha256,
        "solver_sha256": args.solver_sha256,
        "verifier_sha256": args.verifier_sha256,
        "target_centers": TARGET_CENTERS,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()


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
        "campaign_fingerprint": args.campaign_fingerprint,
    }
    if any(result.get(key) != value for key, value in expected.items()):
        return False
    outcome = result.get("outcome")
    if outcome in {"CANCELLED", "ERROR"}:
        return False
    if outcome == "UNKNOWN":
        return result.get("time_limit_seconds", 0) >= args.seconds
    if outcome == "SAT_VERIFIED":
        return result.get("witness_verified") is True
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
        "next_count": 0,
        "projection_cuts": args.projection_cuts,
        "solver": str(args.solver),
        "solver_sha256": args.solver_sha256,
        "generator": str(args.generator),
        "generator_sha256": args.generator_sha256,
        "verifier": str(args.verifier),
        "verifier_sha256": args.verifier_sha256,
        "witness_verified": False,
        "selected_centers": [],
        "proof_status": "none",
        "failed_stage": None,
        "error": None,
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
        args.generator,
        args.weight,
        path,
        args.projection_cuts,
    )
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
            str(args.solver),
            "-t",
            str(args.seconds),
            str(cnf_path),
        ]
        exit_code, elapsed, stop_reason = run_process(
            solver_command,
            temporary_log_path,
            args.seconds + 90,
            args.cancel_event,
        )
        temporary_log_path.replace(log_path)
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
                selected_centers = verify_sat_model(
                    args, node_dir, log_text
                )
                result["outcome"] = "SAT_VERIFIED"
                result["witness_verified"] = True
                result["selected_centers"] = selected_centers
                result["proof_status"] = "direct-witness-verification"

        if (
            result["outcome"] == "UNKNOWN"
            and can_have_remaining_center(path)
        ):
            stage = "orbit_enumeration"
            result["next_count"] = list_next_orbits(
                args.generator,
                args.weight,
                path,
                timeout=args.generation_seconds,
            )
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
        "weight": args.weight,
        "root_path": list(root_path),
        "projection_cuts": args.projection_cuts,
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
    parser.add_argument("--keep-cnf", action="store_true")
    parser.add_argument("--rerun", action="store_true")
    parser.add_argument("--generation-seconds", type=int, default=300)
    parser.add_argument("--minimum-free-gb", type=float, default=2.0)
    parsed = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    parsed.root = root
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
    suffix = "projection" if parsed.projection_cuts else "base"
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
