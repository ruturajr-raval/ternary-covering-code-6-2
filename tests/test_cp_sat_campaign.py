#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import threading
from types import SimpleNamespace
import tempfile


root = Path(__file__).resolve().parent.parent
module_path = root / "tools" / "cp_sat_orbit_campaign.py"
spec = importlib.util.spec_from_file_location(
    "cp_sat_orbit_campaign", module_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


assert module.status_exit_consistent("OPTIMAL", 0)
assert module.status_exit_consistent("FEASIBLE", 0)
assert module.status_exit_consistent("INFEASIBLE", 20)
assert module.status_exit_consistent("UNKNOWN", 3)
assert not module.status_exit_consistent("INFEASIBLE", 0)
assert not module.status_exit_consistent("ERROR", 3)

assert module.node_fingerprint("campaign", 0) != module.node_fingerprint(
    "campaign", 1
)
assert module.node_fingerprint("campaign", 0) != module.node_fingerprint(
    "other", 0
)
assert module.run_fingerprint("campaign", [0], 10, 1) != (
    module.run_fingerprint("campaign", [0, 1], 10, 1)
)
assert module.run_fingerprint("campaign", [0], 10, 1) != (
    module.run_fingerprint("campaign", [0], 20, 1)
)
assert module.run_fingerprint("campaign", [0], 10, 1) != (
    module.run_fingerprint("campaign", [0], 10, 2)
)

full_outcome = module.campaign_outcome(
    [0, 1],
    2,
    {
        0: {"status": "INFEASIBLE"},
        1: {"status": "INFEASIBLE"},
    },
)
assert full_outcome["full_manifest_covered"]
assert full_outcome["solver_excluded"]
subset_outcome = module.campaign_outcome(
    [0],
    2,
    {0: {"status": "INFEASIBLE"}},
)
assert not subset_outcome["full_manifest_covered"]
assert not subset_outcome["solver_excluded"]


def manifest_for_weight(weight):
    anchor = module.anchor_center(weight)
    candidate_max_weight = module.third_candidate_max_weight(weight)
    groups = {}
    for center in range(module.SPACE_SIZE):
        if (
            center in {0, anchor}
            or module.center_weight(center) > candidate_max_weight
        ):
            continue
        groups.setdefault(
            module.third_orbit_key(center, weight), []
        ).append(center)
    orbits = []
    for index, members in enumerate(
        sorted(groups.values(), key=lambda values: min(values))
    ):
        members = sorted(members)
        orbits.append(
            {
                "index": index,
                "representative": module.format_center(members[0]),
                "members": members,
                "members_sha256": module.hashlib.sha256(
                    json.dumps(members).encode()
                ).hexdigest(),
            }
        )
    return {
        "schema": 2,
        "weight": weight,
        "target_centers": 16,
        "exact_cardinality": True,
        "candidate_max_weight": candidate_max_weight,
        "eligible_centers": sum(
            len(orbit["members"]) for orbit in orbits
        ),
        "orbit_count": len(orbits),
        "orbits": orbits,
    }


manifest = manifest_for_weight(5)
module.validate_orbit_manifest(manifest, 5)
assert manifest["orbit_count"] == 24
invalid_manifest = json.loads(json.dumps(manifest))
invalid_manifest["orbits"][0]["members"].pop()
try:
    module.validate_orbit_manifest(invalid_manifest, 5)
except ValueError:
    pass
else:
    raise AssertionError("incomplete orbit manifest was accepted")


results_root = root / "research-results"
results_root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(
    dir=results_root, prefix="cp-sat-campaign-test-"
) as temporary:
    temporary_root = Path(temporary)
    node = temporary_root / "orbit-00"
    result_path = node / "result.json"
    node.mkdir()
    log_path = node / "solve.log"
    log_path.write_text("status: INFEASIBLE\n")
    hashes = {
        "tools/cp_sat_search.py": "a" * 64,
        "build/verify_code": "b" * 64,
    }
    campaign_fingerprint = "campaign"
    args = SimpleNamespace(
        weight=5,
        seconds=60,
        workers_per_job=2,
        seed_base=1000,
        two_projection_cuts=True,
        five_projection_cuts=True,
        campaign_fingerprint=campaign_fingerprint,
        orbit_manifest=manifest,
        orbit_manifest_sha256=module.hash_json(manifest),
        provenance={
            "file_sha256": hashes,
            "environment": {"ortools_version": "test-version"},
        },
    )
    fingerprint = module.node_fingerprint(campaign_fingerprint, 0)
    entry = manifest["orbits"][0]
    result = {
        "schema": 2,
        "status": "INFEASIBLE",
        "weight": 5,
        "third_orbit": 0,
        "time_limit_seconds": 10,
        "workers": 2,
        "seed": 1000,
        "two_projection_cuts": True,
        "five_projection_cuts": True,
        "campaign_fingerprint": fingerprint,
        "exit_code": 20,
        "model_sha256": "c" * 64,
        "script_sha256": hashes["tools/cp_sat_search.py"],
        "verifier_sha256": hashes["build/verify_code"],
        "orbit_members_sha256": entry["members_sha256"],
        "orbit_manifest_sha256": args.orbit_manifest_sha256,
        "orbit_representative": entry["representative"],
        "log_sha256": module.hash_file(log_path),
        "ortools_version": "test-version",
        "command": module.orbit_command(
            args, temporary_root, node, 0, 10
        ),
    }
    result_path.write_text(json.dumps(result))
    assert module.reusable_result(
        result_path,
        args,
        0,
        fingerprint,
        temporary_root,
        result["model_sha256"],
    ) == result

    result["model_sha256"] = "d" * 64
    result_path.write_text(json.dumps(result))
    assert (
        module.reusable_result(
            result_path,
            args,
            0,
            fingerprint,
            temporary_root,
            "c" * 64,
        )
        is None
    )

    result["model_sha256"] = "c" * 64
    result["command"] = ["wrong"]
    result_path.write_text(json.dumps(result))
    assert (
        module.reusable_result(
            result_path,
            args,
            0,
            fingerprint,
            temporary_root,
            result["model_sha256"],
        )
        is None
    )

    result["command"] = module.orbit_command(
        args, temporary_root, node, 0, 10
    )
    log_path.write_text("status: UNKNOWN\n")
    result["log_sha256"] = module.hash_file(log_path)
    result_path.write_text(json.dumps(result))
    assert (
        module.reusable_result(
            result_path,
            args,
            0,
            fingerprint,
            temporary_root,
            result["model_sha256"],
        )
        is None
    )

    lock_output = temporary_root / "lock-test"
    lock_output.mkdir()
    first_lock = module.acquire_campaign_lock(lock_output)
    try:
        try:
            module.acquire_campaign_lock(lock_output)
        except RuntimeError:
            pass
        else:
            raise AssertionError("concurrent campaign lock was accepted")
    finally:
        module.fcntl.flock(
            first_lock.fileno(), module.fcntl.LOCK_UN
        )
        first_lock.close()

    cancelled_output = temporary_root / "cancelled"
    cancelled = threading.Event()
    cancelled.set()
    orbit, cancelled_result, was_cached = module.run_orbit(
        args,
        temporary_root,
        cancelled_output,
        0,
        cancelled,
    )
    assert orbit == 0
    assert not was_cached
    assert cancelled_result["status"] == "CANCELLED"
    recorded = json.loads(
        (
            cancelled_output
            / "orbit-00"
            / "result.json"
        ).read_text()
    )
    assert recorded["status"] == "CANCELLED"

print("CP-SAT campaign tests passed")
