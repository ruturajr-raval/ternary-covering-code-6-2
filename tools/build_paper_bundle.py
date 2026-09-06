#!/usr/bin/env python3

"""Build a deterministic source archive for the technical report."""

import argparse
import gzip
from io import BytesIO
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT
    / "dist"
    / "paper"
    / "ternary-covering-code-6-2-source.tar.gz"
)
MEMBERS = (
    Path("paper/main.tex"),
    Path("paper/README.md"),
    Path("paper/ARXIV_METADATA.md"),
    Path("paper/RIGHTS.md"),
    Path("LICENSE"),
)


def add_member(archive, relative_path):
    data = (ROOT / relative_path).read_bytes()
    info = tarfile.TarInfo(relative_path.as_posix())
    info.size = len(data)
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    archive.addfile(info, fileobj=BytesIO(data))


def build_bundle(output):
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("wb") as raw:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=raw,
            mtime=0,
        ) as compressed:
            with tarfile.open(
                fileobj=compressed,
                mode="w",
                format=tarfile.USTAR_FORMAT,
            ) as archive:
                for member in MEMBERS:
                    add_member(archive, member)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build_bundle(args.output)
    print(f"output={args.output} members={len(MEMBERS)}")


if __name__ == "__main__":
    main()
