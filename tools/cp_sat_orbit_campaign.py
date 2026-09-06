#!/usr/bin/env python3

import argparse
import concurrent.futures
from collections import Counter
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import threading
import time
import uuid


LENGTH = 6
SPACE_SIZE = 3 ** LENGTH
MODEL_SHA_UNSET = object()


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


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    )
    with temporary.open("w") as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


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


def run_process(command, output, timeout, cancel_event, cwd):
    started = time.monotonic()
    process = None
    with output.open("wb") as handle:
        try:
            process = subprocess.Popen(
                command,
                stdout=handle,
                stderr=subprocess.STDOUT,
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
            handle.flush()
            os.fsync(handle.fileno())
            return exit_code, stop_reason
        finally:
            if process is not None and process.poll() is None:
                terminate_process(process)


def format_center(center):
    digits = ["0"] * LENGTH
    value = center
    for index in range(LENGTH - 1, -1, -1):
        digits[index] = str(value % 3)
        value //= 3
    return "".join(digits)


def center_weight(center):
    result = 0
    value = center
    for _ in range(LENGTH):
        result += value % 3 != 0
        value //= 3
    return result


def center_digits(center):
    digits = [0] * LENGTH
    value = center
    for index in range(LENGTH - 1, -1, -1):
        digits[index] = value % 3
        value //= 3
    return digits


def third_orbit_key(center, weight):
    digits = center_digits(center)
    support = digits[:weight]
    return (
        support.count(0),
        support.count(1),
        support.count(2),
        sum(digit != 0 for digit in digits[weight:]),
    )


def anchor_center(weight):
    value = 0
    for coordinate in range(LENGTH):
        value = 3 * value + (1 if coordinate < weight else 0)
    return value


def validate_orbit_manifest(manifest, weight):
    if (
        manifest.get("schema") != 1
        or manifest.get("weight") != weight
        or not isinstance(manifest.get("orbits"), list)
    ):
        raise ValueError("invalid third-orbit manifest header")
    anchor = anchor_center(weight)
    allowed = {
        center
        for center in range(SPACE_SIZE)
        if center not in {0, anchor}
        and center_weight(center) <= weight
    }
    expected_groups = {}
    for center in allowed:
        expected_groups.setdefault(
            third_orbit_key(center, weight), []
        ).append(center)
    expected_orbits = sorted(
        (sorted(members) for members in expected_groups.values()),
        key=lambda members: members[0],
    )
    if len(manifest["orbits"]) != len(expected_orbits):
        raise ValueError("third-orbit manifest has the wrong orbit count")
    covered = set()
    for expected_index, (entry, expected_members) in enumerate(
        zip(manifest["orbits"], expected_orbits)
    ):
        members = entry.get("members")
        if (
            entry.get("index") != expected_index
            or not isinstance(members, list)
            or not members
            or members != sorted(set(members))
            or any(
                not isinstance(center, int)
                or center < 0
                or center >= SPACE_SIZE
                for center in members
            )
        ):
            raise ValueError("invalid third-orbit manifest entry")
        if members != expected_members:
            raise ValueError("third-orbit manifest has invalid membership")
        member_set = set(members)
        if covered.intersection(member_set):
            raise ValueError("third-orbit manifest overlaps")
        representative = min(members)
        if (
            entry.get("representative") != format_center(representative)
            or entry.get("members_sha256")
            != hashlib.sha256(
                json.dumps(members).encode()
            ).hexdigest()
        ):
            raise ValueError("third-orbit manifest hash mismatch")
        covered.update(member_set)
    if (
        covered != allowed
        or manifest.get("allowed_centers") != len(allowed)
        or manifest.get("orbit_count") != len(manifest["orbits"])
    ):
        raise ValueError("third-orbit manifest is not exhaustive")


def load_orbit_manifest(root, args):
    python = root / ".tools" / "ortools-venv" / "bin" / "python"
    completed = subprocess.run(
        [
            str(python),
            str(root / "tools" / "cp_sat_search.py"),
            "--weight",
            str(args.weight),
            "--list-third-orbits-json",
        ],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads(completed.stdout)
    validate_orbit_manifest(manifest, args.weight)
    return manifest


def load_model_metadata(root, args, orbit):
    python = root / ".tools" / "ortools-venv" / "bin" / "python"
    command = [
        str(python),
        str(root / "tools" / "cp_sat_search.py"),
        "--weight",
        str(args.weight),
        "--third-orbit",
        str(orbit),
        "--model-metadata-json",
    ]
    if args.two_projection_cuts:
        command.append("--two-projection-cuts")
    else:
        command.append("--no-two-projection-cuts")
    if args.five_projection_cuts:
        command.append("--five-projection-cuts")
    completed = subprocess.run(
        command,
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    metadata = json.loads(completed.stdout)
    entry = args.orbit_manifest["orbits"][orbit]
    expected = {
        "schema": 1,
        "weight": args.weight,
        "third_orbit": orbit,
        "two_projection_cuts": args.two_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "orbit_representative": entry["representative"],
        "orbit_members_sha256": entry["members_sha256"],
        "orbit_manifest_sha256": args.orbit_manifest_sha256,
        "ortools_version": (
            args.provenance["environment"]["ortools_version"]
        ),
    }
    mismatches = [
        key
        for key, value in expected.items()
        if metadata.get(key) != value
    ]
    digest = metadata.get("model_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        mismatches.append("model_sha256")
    if mismatches:
        raise RuntimeError(
            "model metadata mismatch: " + ",".join(sorted(set(mismatches)))
        )
    return metadata


def git_provenance(root):
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    diff = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
    ).stdout
    return {
        "git_commit": commit,
        "git_status_sha256": hashlib.sha256(
            status.encode()
        ).hexdigest(),
        "git_diff_sha256": hashlib.sha256(diff).hexdigest(),
        "git_dirty": bool(status.strip()),
    }


def build_provenance(root, args):
    python = root / ".tools" / "ortools-venv" / "bin" / "python"
    environment = json.loads(
        subprocess.run(
            [
                str(python),
                "-c",
                (
                    "import json,ortools,platform,sys;"
                    "print(json.dumps({"
                    "'ortools_version':ortools.__version__,"
                    "'python_version':platform.python_version(),"
                    "'platform':platform.platform(),"
                    "'executable':str(sys.executable)"
                    "},sort_keys=True))"
                ),
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    freeze = subprocess.run(
        [str(python), "-m", "pip", "freeze"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    environment["executable"] = ".tools/ortools-venv/bin/python"
    tracked_files = [
        root / "tools" / "cp_sat_search.py",
        root / "tools" / "cp_sat_orbit_campaign.py",
        root / "tools" / "bootstrap_ortools.sh",
        root / "tools" / "ortools-requirements.lock",
        root / "tools" / "ortools-ci-requirements.lock",
        root / "build" / "verify_code",
    ]
    payload = {
        "schema": 3,
        "weight": args.weight,
        "two_projection_cuts": args.two_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "workers_per_job": args.workers_per_job,
        "seed_base": args.seed_base,
        "orbit_manifest_sha256": args.orbit_manifest_sha256,
        "environment": environment,
        "pip_freeze_sha256": hashlib.sha256(
            freeze.encode()
        ).hexdigest(),
        "python_sha256": hash_file(python.resolve()),
        "file_sha256": {
            str(path.relative_to(root)): hash_file(path)
            for path in tracked_files
        },
        **git_provenance(root),
    }
    return hash_json(payload), payload


def node_fingerprint(campaign_fingerprint, orbit):
    return hashlib.sha256(
        f"{campaign_fingerprint}:{orbit}".encode()
    ).hexdigest()


def run_fingerprint(campaign_fingerprint, selected_orbits, seconds, jobs):
    return hash_json(
        {
            "campaign_fingerprint": campaign_fingerprint,
            "selected_orbits": selected_orbits,
            "time_limit_seconds": seconds,
            "jobs": jobs,
        }
    )


def orbit_command(args, root, node, orbit, seconds=None):
    try:
        relative_node = node.relative_to(root)
    except ValueError:
        relative_node = node
    command = [
        ".tools/ortools-venv/bin/python",
        "tools/cp_sat_search.py",
        "--weight",
        str(args.weight),
        "--third-orbit",
        str(orbit),
        "--seconds",
        str(args.seconds if seconds is None else seconds),
        "--workers",
        str(args.workers_per_job),
        "--seed",
        str(args.seed_base + orbit),
        "--output",
        str(relative_node / "solution.txt"),
        "--result-json",
        str(relative_node / "result.json"),
        "--campaign-fingerprint",
        node_fingerprint(args.campaign_fingerprint, orbit),
    ]
    if args.two_projection_cuts:
        command.append("--two-projection-cuts")
    else:
        command.append("--no-two-projection-cuts")
    if args.five_projection_cuts:
        command.append("--five-projection-cuts")
    return command


def status_exit_consistent(status, exit_code):
    expected = {
        "OPTIMAL": 0,
        "FEASIBLE": 0,
        "INFEASIBLE": 20,
        "UNKNOWN": 3,
    }
    return status in expected and expected[status] == exit_code


def log_status(path):
    statuses = re.findall(
        r"^status: (OPTIMAL|FEASIBLE|INFEASIBLE|UNKNOWN)$",
        path.read_text(errors="replace"),
        flags=re.MULTILINE,
    )
    return statuses[0] if len(statuses) == 1 else None


def parse_witness(path):
    words = [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip()
    ]
    if (
        len(words) != 16
        or len(set(words)) != 16
        or any(re.fullmatch(r"[012]{6}", word) is None for word in words)
    ):
        return None
    return words


def verify_cached_witness(root, result, args, orbit):
    witness = result.get("witness_path")
    if not witness:
        return False
    witness_path = Path(witness)
    if not witness_path.is_absolute():
        witness_path = root / witness_path
    if (
        not witness_path.exists()
        or result.get("witness_sha256") != hash_file(witness_path)
    ):
        return False
    words = parse_witness(witness_path)
    if words is None or words != result.get("selected_centers"):
        return False

    entry = args.orbit_manifest["orbits"][orbit]
    selected = {
        int(word, 3)
        for word in words
    }
    earlier = {
        center
        for previous in args.orbit_manifest["orbits"][:orbit]
        for center in previous["members"]
    }
    if (
        0 not in selected
        or anchor_center(args.weight) not in selected
        or int(entry["representative"], 3) not in selected
        or selected.intersection(earlier)
        or any(center_weight(center) > args.weight for center in selected)
    ):
        return False

    completed = subprocess.run(
        [str(root / "build" / "verify_code"), str(witness_path)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    expected = {"centers: 16", "distinct: yes", "holes: 0"}
    return (
        completed.returncode == 0
        and expected.issubset(set(completed.stdout.splitlines()))
    )


def result_record_issues(
    path,
    result,
    args,
    orbit,
    fingerprint,
    root,
    expected_model_sha256=None,
):
    entry = args.orbit_manifest["orbits"][orbit]
    issues = []
    expected = {
        "schema": 2,
        "weight": args.weight,
        "third_orbit": orbit,
        "workers": args.workers_per_job,
        "seed": args.seed_base + orbit,
        "two_projection_cuts": args.two_projection_cuts,
        "five_projection_cuts": args.five_projection_cuts,
        "campaign_fingerprint": fingerprint,
        "orbit_representative": entry["representative"],
        "orbit_members_sha256": entry["members_sha256"],
        "orbit_manifest_sha256": args.orbit_manifest_sha256,
        "ortools_version": (
            args.provenance["environment"]["ortools_version"]
        ),
    }
    issues.extend(
        key
        for key, value in expected.items()
        if result.get(key) != value
    )

    required_hashes = (
        "model_sha256",
        "script_sha256",
        "verifier_sha256",
        "orbit_members_sha256",
        "orbit_manifest_sha256",
        "log_sha256",
    )
    issues.extend(
        key
        for key in required_hashes
        if not isinstance(result.get(key), str)
        or len(result[key]) != 64
    )
    expected_files = args.provenance["file_sha256"]
    if (
        result.get("script_sha256")
        != expected_files["tools/cp_sat_search.py"]
    ):
        issues.append("script_sha256_value")
    if (
        result.get("verifier_sha256")
        != expected_files["build/verify_code"]
    ):
        issues.append("verifier_sha256_value")
    if (
        expected_model_sha256 is not None
        and result.get("model_sha256") != expected_model_sha256
    ):
        issues.append("model_sha256_value")

    recorded_seconds = result.get("time_limit_seconds")
    if (
        not isinstance(recorded_seconds, (int, float))
        or recorded_seconds <= 0
    ):
        issues.append("time_limit_seconds")
    else:
        expected_command = orbit_command(
            args,
            root,
            path.parent,
            orbit,
            recorded_seconds,
        )
        if result.get("command") != expected_command:
            issues.append("command")

    log_path = path.parent / "solve.log"
    if not log_path.exists():
        issues.append("solve.log")
    else:
        if result.get("log_sha256") != hash_file(log_path):
            issues.append("log_sha256_value")
        if result.get("status") != log_status(log_path):
            issues.append("log_status")

    if not status_exit_consistent(
        result.get("status"), result.get("exit_code")
    ):
        issues.append("status_exit")
    if result.get("status") in {"OPTIMAL", "FEASIBLE"}:
        if (
            result.get("witness_verified") is not True
            or not verify_cached_witness(root, result, args, orbit)
        ):
            issues.append("witness")
    return sorted(set(issues))


def reusable_result(
    path,
    args,
    orbit,
    fingerprint,
    root,
    expected_model_sha256=MODEL_SHA_UNSET,
):
    if not path.exists():
        return None
    try:
        result = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if expected_model_sha256 is MODEL_SHA_UNSET:
        expected_model_sha256 = load_model_metadata(
            root, args, orbit
        )["model_sha256"]
    if result_record_issues(
        path,
        result,
        args,
        orbit,
        fingerprint,
        root,
        expected_model_sha256,
    ):
        return None
    if result["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE"}:
        return result
    if (
        result["status"] == "UNKNOWN"
        and result["time_limit_seconds"] >= args.seconds
    ):
        return result
    return None


def error_result(args, orbit, fingerprint, message, command=None):
    return {
        "schema": 3,
        "status": "ERROR",
        "weight": args.weight,
        "third_orbit": orbit,
        "campaign_fingerprint": fingerprint,
        "command": command or [],
        "error": message,
    }


def cancelled_result(args, orbit, fingerprint, command=None):
    result = error_result(
        args,
        orbit,
        fingerprint,
        "campaign cancellation requested",
        command,
    )
    result["status"] = "CANCELLED"
    return result


def run_orbit(args, root, output, orbit, cancel_event):
    node = output / f"orbit-{orbit:02d}"
    node.mkdir(parents=True, exist_ok=True)
    result_path = node / "result.json"
    fingerprint = node_fingerprint(args.campaign_fingerprint, orbit)
    reusable = reusable_result(
        result_path, args, orbit, fingerprint, root
    )
    if reusable is not None:
        return orbit, reusable, True
    if cancel_event.is_set():
        result = cancelled_result(args, orbit, fingerprint)
        write_json(result_path, result)
        return orbit, result, False

    command = orbit_command(args, root, node, orbit)
    log_path = node / "solve.log"
    temporary_log = node / (
        f"solve.log.{os.getpid()}.{threading.get_ident()}."
        f"{uuid.uuid4().hex}.tmp"
    )
    result_path.unlink(missing_ok=True)
    (node / "solution.txt").unlink(missing_ok=True)
    try:
        exit_code, stop_reason = run_process(
            command,
            temporary_log,
            args.seconds + 30,
            cancel_event,
            root,
        )
        temporary_log.replace(log_path)
        if stop_reason == "cancelled":
            result = cancelled_result(
                args, orbit, fingerprint, command
            )
            result["exit_code"] = exit_code
            result["log_sha256"] = hash_file(log_path)
        elif stop_reason == "timeout":
            result = error_result(
                args,
                orbit,
                fingerprint,
                "solver exceeded the external shutdown limit",
                command,
            )
            result["exit_code"] = exit_code
            result["log_sha256"] = hash_file(log_path)
        elif not result_path.exists():
            result = error_result(
                args,
                orbit,
                fingerprint,
                "solver did not write a result record",
                command,
            )
            result["exit_code"] = exit_code
            result["log_sha256"] = hash_file(log_path)
        else:
            try:
                result = json.loads(result_path.read_text())
            except (json.JSONDecodeError, OSError) as error:
                result = error_result(
                    args,
                    orbit,
                    fingerprint,
                    f"invalid result record: {error}",
                    command,
                )
            result["exit_code"] = exit_code
            result["command"] = command
            result["log_sha256"] = hash_file(log_path)
            issues = result_record_issues(
                result_path,
                result,
                args,
                orbit,
                fingerprint,
                root,
            )
            if issues:
                result = error_result(
                    args,
                    orbit,
                    fingerprint,
                    "incompatible result fields: " + ",".join(issues),
                    command,
                )
                result["exit_code"] = exit_code
                result["log_sha256"] = hash_file(log_path)
        write_json(result_path, result)
        return orbit, result, False
    finally:
        temporary_log.unlink(missing_ok=True)


def campaign_outcome(selected_orbits, orbit_count, results):
    statuses = Counter(
        result["status"] for result in results.values()
    )
    all_results_present = len(results) == len(selected_orbits)
    full_manifest_covered = selected_orbits == list(range(orbit_count))
    solver_excluded = (
        all_results_present
        and full_manifest_covered
        and len(statuses) == 1
        and statuses["INFEASIBLE"] == orbit_count
    )
    witness_found = any(
        result["status"] in {"OPTIMAL", "FEASIBLE"}
        and result.get("witness_verified") is True
        for result in results.values()
    )
    return {
        "statuses": statuses,
        "all_results_present": all_results_present,
        "full_manifest_covered": full_manifest_covered,
        "solver_excluded": solver_excluded,
        "witness_found": witness_found,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=int, required=True, choices=(4, 5, 6))
    parser.add_argument("--seconds", type=float, default=120)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--workers-per-job", type=int, default=2)
    parser.add_argument("--seed-base", type=int, default=1000)
    parser.add_argument(
        "--two-projection-cuts",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    parser.add_argument("--five-projection-cuts", action="store_true")
    parser.add_argument("--orbit", type=int, action="append")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if (
        args.seconds <= 0
        or args.jobs <= 0
        or args.workers_per_job <= 0
    ):
        raise SystemExit("seconds, jobs, and workers per job must be positive")

    root = Path(__file__).resolve().parent.parent
    args.orbit_manifest = load_orbit_manifest(root, args)
    args.orbit_manifest_sha256 = hash_json(args.orbit_manifest)
    args.orbit_count = args.orbit_manifest["orbit_count"]
    if args.orbit is None:
        args.selected_orbits = list(range(args.orbit_count))
    else:
        args.selected_orbits = sorted(set(args.orbit))
        if (
            not args.selected_orbits
            or args.selected_orbits[0] < 0
            or args.selected_orbits[-1] >= args.orbit_count
        ):
            raise SystemExit(
                f"orbit must be in 0..{args.orbit_count - 1}"
            )
    (
        args.campaign_fingerprint,
        args.provenance,
    ) = build_provenance(root, args)
    args.run_fingerprint = run_fingerprint(
        args.campaign_fingerprint,
        args.selected_orbits,
        args.seconds,
        args.jobs,
    )
    output = args.output
    if output is None:
        cuts = []
        if args.two_projection_cuts:
            cuts.append("p2")
        if args.five_projection_cuts:
            cuts.append("p5")
        suffix = "_".join(cuts) if cuts else "base"
        output = (
            root
            / "research-results"
            / "cp-sat"
            / f"w{args.weight}_third_orbits_{suffix}"
        )
    elif not output.is_absolute():
        output = root / output
    output.mkdir(parents=True, exist_ok=True)

    try:
        campaign_lock = acquire_campaign_lock(output)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 4

    cancel_event = threading.Event()
    interrupt_signal = [None]

    def handle_signal(signum, _frame):
        if interrupt_signal[0] is None:
            interrupt_signal[0] = int(signum)
        cancel_event.set()

    previous_handlers = {
        signum: signal.getsignal(signum)
        for signum in (signal.SIGINT, signal.SIGTERM)
    }
    for signum in previous_handlers:
        signal.signal(signum, handle_signal)

    results = {}
    cached = 0
    try:
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=args.jobs
        ) as executor:
            futures = {
                executor.submit(
                    run_orbit,
                    args,
                    root,
                    output,
                    orbit,
                    cancel_event,
                ): orbit
                for orbit in args.selected_orbits
            }
            for future in concurrent.futures.as_completed(futures):
                orbit = futures[future]
                try:
                    orbit, result, was_cached = future.result()
                except concurrent.futures.CancelledError:
                    continue
                except Exception as error:
                    fingerprint = node_fingerprint(
                        args.campaign_fingerprint, orbit
                    )
                    result = error_result(
                        args,
                        orbit,
                        fingerprint,
                        f"{type(error).__name__}: {error}",
                    )
                    write_json(
                        output / f"orbit-{orbit:02d}" / "result.json",
                        result,
                    )
                    was_cached = False
                results[orbit] = result
                cached += was_cached
                print(
                    f"orbit {orbit}: {result['status']}"
                    f"{' cached' if was_cached else ''}",
                    flush=True,
                )
                if result["status"] in {"OPTIMAL", "FEASIBLE"}:
                    cancel_event.set()
                    for pending in futures:
                        pending.cancel()

        outcome = campaign_outcome(
            args.selected_orbits,
            args.orbit_count,
            results,
        )
        statuses = outcome["statuses"]
        all_results_present = outcome["all_results_present"]
        full_manifest_covered = outcome["full_manifest_covered"]
        solver_excluded = outcome["solver_excluded"]
        witness_found = outcome["witness_found"]
        operational_errors = statuses["ERROR"]
        summary = {
            "schema": 4,
            "weight": args.weight,
            "orbit_count": args.orbit_count,
            "selected_orbits": args.selected_orbits,
            "full_manifest_covered": full_manifest_covered,
            "orbit_manifest": args.orbit_manifest,
            "orbit_manifest_sha256": args.orbit_manifest_sha256,
            "time_limit_seconds": args.seconds,
            "jobs": args.jobs,
            "workers_per_job": args.workers_per_job,
            "two_projection_cuts": args.two_projection_cuts,
            "five_projection_cuts": args.five_projection_cuts,
            "results": len(results),
            "cached": cached,
            "statuses": dict(sorted(statuses.items())),
            "all_results_present": all_results_present,
            "solver_excluded": solver_excluded,
            "witness_found": witness_found,
            "proof_status": (
                "solver-only-no-certificate"
                if solver_excluded
                else "not-generated"
            ),
            "campaign_fingerprint": args.campaign_fingerprint,
            "run_fingerprint": args.run_fingerprint,
            "interrupted": interrupt_signal[0] is not None,
            "interrupt_signal": interrupt_signal[0],
            "provenance": args.provenance,
        }
        write_json(output / "summary.json", summary)
        print(json.dumps(summary, indent=2, sort_keys=True))
        if witness_found:
            return 0
        if interrupt_signal[0] is not None:
            return 128 + interrupt_signal[0]
        if solver_excluded:
            return 2
        if operational_errors:
            return 4
        return 3
    finally:
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        fcntl.flock(campaign_lock.fileno(), fcntl.LOCK_UN)
        campaign_lock.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:
        print(f"error: {type(error).__name__}: {error}", file=sys.stderr)
        raise SystemExit(4) from error
