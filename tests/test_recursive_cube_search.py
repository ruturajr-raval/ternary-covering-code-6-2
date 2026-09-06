#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace


project_root = Path(__file__).resolve().parent.parent
module_path = project_root / "tools" / "recursive_cube_search.py"
spec = importlib.util.spec_from_file_location("recursive_cube_search", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


assert module.parse_path("") == ()
assert module.parse_path("0,2,11") == (0, 2, 11)
try:
    module.parse_path("0,-1")
except ValueError:
    pass
else:
    raise AssertionError("negative orbit index was accepted")

assert module.classify_log("s SATISFIABLE\nv 1 0\n") == "SAT"
assert module.classify_log("s UNSATISFIABLE\n") == "UNSAT"
assert module.classify_log("c UNKNOWN\n") == "UNKNOWN"
assert module.classify_log("s UNKNOWN\n") == "UNKNOWN"
assert module.classify_log("solver failed\n") == "ERROR"
assert module.classify_log(
    "s SATISFIABLE\ns UNSATISFIABLE\n"
) == "ERROR"

assert module.solver_result_is_consistent("SAT", 10)
assert module.solver_result_is_consistent("UNSAT", 20)
assert module.solver_result_is_consistent("UNKNOWN", 0)
assert not module.solver_result_is_consistent("SAT", 0)

assert module.format_center(0) == "000000"
assert module.format_center(728) == "222222"

model = "s SATISFIABLE\nv " + " ".join(
    str(variable if variable <= 16 else -variable)
    for variable in range(1, module.SPACE_SIZE + 1)
) + " 0\n"
assert module.selected_centers_from_model(model) == list(range(16))

assert module.can_have_remaining_center((0,) * 13)
assert not module.can_have_remaining_center((0,) * 14)

tree_root = ()
children = {
    tree_root: {"outcome": "UNKNOWN", "next_count": 2},
    (0,): {"outcome": "SOLVER_UNSAT", "next_count": 0},
    (1,): {"outcome": "UNSAT_VERIFIED", "next_count": 0},
}
assert module.reduce_tree(tree_root, children, 8) == "SOLVER_CLOSED"
del children[(1,)]
assert module.reduce_tree(tree_root, children, 8) == "DEFERRED"
assert module.reduce_tree(
    tree_root,
    {tree_root: {"outcome": "UNKNOWN", "next_count": 2}},
    0,
) == "OPEN"


def write_executable(path, text):
    path.write_text(text)
    path.chmod(0o755)


def make_args(root, generator, solver, verifier, name):
    args = SimpleNamespace(
        root=root,
        output=root / name,
        generator=generator,
        solver=solver,
        verifier=verifier,
        weight=4,
        projection_cuts=False,
        seconds=2,
        generation_seconds=5,
        minimum_free_bytes=0,
        keep_cnf=False,
        rerun=False,
        cancel_event=threading.Event(),
        storage_lock=threading.Lock(),
        generation_lock_path=root / ".generation.lock",
    )
    args.output.mkdir()
    args.generator_sha256 = module.hash_file(generator)
    args.solver_sha256 = module.hash_file(solver)
    args.verifier_sha256 = module.hash_file(verifier)
    args.campaign_fingerprint = module.campaign_fingerprint(args)
    return args


results_root = project_root / "research-results"
results_root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(
    dir=results_root, prefix="coordinator-test-"
) as temporary:
    temporary_root = Path(temporary)
    generator = temporary_root / "generator.py"
    verifier = temporary_root / "verifier.py"
    sat_solver = temporary_root / "sat_solver.py"
    unknown_solver = temporary_root / "unknown_solver.py"
    contradictory_solver = temporary_root / "contradictory_solver.py"

    write_executable(
        generator,
        """#!/usr/bin/env python3
import sys
if "--list-next-orbits" in sys.argv:
    print("0 000001 orbit_size=1")
    print("1 000002 orbit_size=1")
else:
    print("p cnf 729 0")
""",
    )
    write_executable(
        verifier,
        """#!/usr/bin/env python3
print("centers: 16")
print("distinct: yes")
print("holes: 0")
""",
    )
    assignment = " ".join(
        str(variable if variable <= 16 else -variable)
        for variable in range(1, module.SPACE_SIZE + 1)
    )
    write_executable(
        sat_solver,
        f"""#!/usr/bin/env python3
import sys
print("s SATISFIABLE")
print("v {assignment} 0")
sys.exit(10)
""",
    )
    write_executable(
        unknown_solver,
        """#!/usr/bin/env python3
print("c UNKNOWN")
""",
    )
    write_executable(
        contradictory_solver,
        """#!/usr/bin/env python3
import sys
print("s SATISFIABLE")
print("s UNSATISFIABLE")
sys.exit(20)
""",
    )

    sat_args = make_args(
        temporary_root,
        generator,
        sat_solver,
        verifier,
        "sat",
    )
    sat_result = module.run_node(sat_args, (0,))
    assert sat_result["outcome"] == "SAT_VERIFIED"
    assert sat_result["witness_verified"]
    assert len(sat_result["selected_centers"]) == 16
    assert (sat_args.output / "0" / "case.cnf").exists()

    unknown_args = make_args(
        temporary_root,
        generator,
        unknown_solver,
        verifier,
        "unknown",
    )
    unknown_result = module.run_node(unknown_args, (0,))
    assert unknown_result["outcome"] == "UNKNOWN"
    assert unknown_result["next_count"] == 2
    assert not (unknown_args.output / "0" / "case.cnf").exists()
    assert module.cached_result(unknown_args, (0,)) == unknown_result

    contradictory_args = make_args(
        temporary_root,
        generator,
        contradictory_solver,
        verifier,
        "contradictory",
    )
    contradictory_result = module.run_node(contradictory_args, (0,))
    assert contradictory_result["outcome"] == "ERROR"
    assert contradictory_result["failed_stage"] == "solving"
    assert (contradictory_args.output / "0" / "case.cnf").exists()

    lock_root = temporary_root / "lock"
    lock_root.mkdir()
    first_lock = module.acquire_campaign_lock(lock_root)
    try:
        try:
            module.acquire_campaign_lock(lock_root)
        except RuntimeError:
            pass
        else:
            raise AssertionError("concurrent campaign lock was accepted")
    finally:
        module.fcntl.flock(first_lock.fileno(), module.fcntl.LOCK_UN)
        first_lock.close()

print("recursive coordinator tests passed")
