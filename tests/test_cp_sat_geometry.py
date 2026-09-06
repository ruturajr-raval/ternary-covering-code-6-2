#!/usr/bin/env python3

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


root = Path(__file__).resolve().parent.parent
module_path = root / "tools" / "cp_sat_search.py"
spec = importlib.util.spec_from_file_location(
    "cp_sat_search", module_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


assert module.SPHERE_SIZES == (1, 12, 60, 160, 240, 192, 64)
assert module.SPHERE_CAPACITIES == (
    (1, 1, 1, 0, 0, 0, 0),
    (12, 12, 4, 3, 0, 0, 0),
    (60, 20, 20, 9, 6, 0, 0),
    (0, 40, 24, 25, 16, 10, 0),
    (0, 0, 24, 24, 27, 25, 15),
    (0, 0, 0, 12, 20, 26, 36),
    (0, 0, 0, 0, 4, 12, 22),
)
assert {
    weight: len(module.third_orbits(weight))
    for weight in (4, 5, 6)
} == {4: 29, 5: 34, 6: 26}

for weight in (4, 5, 6):
    args = SimpleNamespace(
        weight=weight,
        third_orbit=0,
        two_projection_cuts=True,
        five_projection_cuts=True,
    )
    model, _ = module.build_model(args)
    assert not model.Validate()

metadata_args = SimpleNamespace(
    weight=5,
    third_orbit=0,
    two_projection_cuts=True,
    five_projection_cuts=True,
)
metadata_model, _ = module.build_model(metadata_args)
identity = module.model_identity(
    metadata_args,
    module.model_sha256(metadata_model),
)
completed = subprocess.run(
    [
        sys.executable,
        str(module_path),
        "--weight",
        "5",
        "--third-orbit",
        "0",
        "--five-projection-cuts",
        "--model-metadata-json",
    ],
    cwd=root,
    check=True,
    capture_output=True,
    text=True,
)
metadata = json.loads(completed.stdout)
assert metadata["schema"] == 1
assert all(metadata[key] == value for key, value in identity.items())
assert module.solver_exit_code("OPTIMAL") == 0
assert module.solver_exit_code("INFEASIBLE") == 20
assert module.solver_exit_code("UNKNOWN") == 3
assert module.solver_exit_code("MODEL_INVALID") == 4

print("CP-SAT geometry tests passed")
