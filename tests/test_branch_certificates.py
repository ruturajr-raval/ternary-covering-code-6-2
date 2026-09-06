#!/usr/bin/env python3

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess


root = Path(__file__).resolve().parent.parent
module_path = root / "tools" / "verify_branch_certificates.py"
spec = importlib.util.spec_from_file_location(
    "verify_branch_certificates", module_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

document = json.loads(
    (root / "data" / "weighted_branch_certificates.json").read_text()
)
target_centers = document["target_centers"]
certificates = document["certificates"]

for certificate in certificates:
    module.verify_certificate(certificate, target_centers)
    (
        representative,
        fixed,
        forbidden,
        admissible,
        _,
    ) = module.branch_data(
        certificate["anchor_weight"],
        certificate["third_orbit"],
    )
    manifest = json.loads(
        subprocess.run(
            [
                str(root / "build" / "generate_cnf"),
                "--anchor-weight",
                str(certificate["anchor_weight"]),
                "--third-orbit",
                str(certificate["third_orbit"]),
                "--branch-manifest-json",
            ],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
    )
    assert manifest["schema"] == 1
    assert manifest["representative"] == module.format_word(
        module.WORDS[representative]
    )
    assert manifest["fixed_centers"] == sorted(fixed)
    assert manifest["forbidden_centers"] == sorted(forbidden)
    assert manifest["admissible_centers"] == list(admissible)


def require_rejection(mutator):
    certificate = deepcopy(certificates[0])
    mutator(certificate)
    try:
        module.verify_certificate(certificate, target_centers)
    except AssertionError:
        return
    raise AssertionError("mutated branch certificate was accepted")


require_rejection(
    lambda certificate: certificate.__setitem__(
        "representative", "011120"
    )
)
require_rejection(
    lambda certificate: certificate["weights"][0].__setitem__(
        "orbit_size",
        certificate["weights"][0]["orbit_size"] + 1,
    )
)
require_rejection(
    lambda certificate: certificate.__setitem__(
        "expected_total_weight",
        certificate["expected_total_weight"] + 1,
    )
)
require_rejection(
    lambda certificate: certificate.__setitem__(
        "expected_max_capacity",
        certificate["expected_max_capacity"] - 1,
    )
)
require_rejection(
    lambda certificate: certificate["weights"][0].__setitem__("weight", 0)
)
require_rejection(
    lambda certificate: certificate["weights"][0].__setitem__(
        "weight", 0.5
    )
)
require_rejection(
    lambda certificate: certificate["weights"][0].__setitem__(
        "weight", True
    )
)
require_rejection(
    lambda certificate: certificate["weights"].append(
        deepcopy(certificate["weights"][0])
    )
)

print("branch certificate mutation tests passed")
