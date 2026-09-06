#!/usr/bin/env python3

import importlib.util
from pathlib import Path
import tempfile


root = Path(__file__).resolve().parent.parent
module_path = root / "tools" / "package_campaign.py"
spec = importlib.util.spec_from_file_location(
    "package_campaign", module_path
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

commit = "a" * 40
metadata = module.campaign_metadata(
    {
        "provenance": {
            "git_commit": commit,
            "git_dirty": False,
        },
        "witness_found": True,
    },
    commit,
    False,
)
assert metadata["certified"]

exploratory = module.campaign_metadata(
    {
        "provenance": {
            "git_commit": commit,
            "git_dirty": False,
        },
    },
    commit,
    True,
)
assert not exploratory["certified"]

try:
    module.campaign_metadata(
        {
            "git_commit": commit,
            "git_tracked_dirty": False,
            "run": {"certified_complete": False},
        },
        commit,
        False,
    )
except ValueError:
    pass
else:
    raise AssertionError("noncertified campaign was accepted")

try:
    module.campaign_metadata(
        {
            "provenance": {
                "git_commit": commit,
                "git_dirty": False,
            },
            "witness_found": True,
        },
        "b" * 40,
        False,
    )
except ValueError:
    pass
else:
    raise AssertionError("campaign from another commit was accepted")

results_root = root / "research-results"
results_root.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(
    dir=results_root, prefix="package-test-"
) as temporary:
    temporary_root = Path(temporary)
    safe = temporary_root / "safe.log"
    safe.write_text("status: INFEASIBLE\n")
    assert len(module.hash_and_scan(safe, root.resolve())) == 64

    unsafe = temporary_root / "unsafe.log"
    unsafe.write_text("/" + "Users/example/project/result.json\n")
    try:
        module.hash_and_scan(unsafe, root.resolve())
    except ValueError:
        pass
    else:
        raise AssertionError("home path was accepted")

    collection = temporary_root / "collection"
    collection.mkdir()
    (collection / "summary.json").write_text("{}\n")
    (collection / "solve.log").write_text("status: INFEASIBLE\n")
    (collection / ".campaign.lock").write_text("123\n")
    (collection / "partial.tmp").write_text("temporary\n")
    records, excluded = module.collect_files(collection, root.resolve())
    assert {record["path"] for record in records} == {
        "solve.log",
        "summary.json",
    }
    assert excluded == [".campaign.lock", "partial.tmp"]

    cp_collection = temporary_root / "cp-collection"
    cp_collection.mkdir()
    cp_summary = {
        "orbit_manifest": {"orbit_count": 1},
        "selected_orbits": [0],
    }
    (cp_collection / "orbit-00").mkdir()
    module.validate_campaign_layout(cp_collection, cp_summary)
    (cp_collection / "orbit-24").mkdir()
    try:
        module.validate_campaign_layout(cp_collection, cp_summary)
    except ValueError:
        pass
    else:
        raise AssertionError("unselected CP-SAT branch was accepted")

    (collection / "linked.log").symlink_to(collection / "solve.log")
    try:
        module.collect_files(collection, root.resolve())
    except ValueError:
        pass
    else:
        raise AssertionError("symbolic link was accepted")

print("campaign packaging tests passed")
