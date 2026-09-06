# Third-Party Notices

## Reference 17-Word Code

`data/reference_17_code.txt` is transcribed from the explicit
`K_3(6,2) <= 17` certificate in `florath/covering-codes-lean`.

- Source:
  https://github.com/florath/covering-codes-lean/blob/main/CoveringCodes/Database/Sources/SmallExplicitUpper/K_3_6_2.lean
- Project license: BSD 3-Clause
- Copyright notice: retained by the upstream project and its contributors

The fixture is used only to test the standalone verifier and search tools.
No upstream implementation code is included here.

The redistributed fixture is covered by the following upstream license:

```text
BSD 3-Clause License

Copyright (c) 2026, Andreas Florath

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its contributors
   may be used to endorse or promote products derived from this software
   without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
POSSIBILITY OF SUCH DAMAGE.
```

## Optional SAT Solvers

`tools/bootstrap_solvers.sh` downloads and builds pinned revisions of:

- CaDiCaL, commit `c60730422e758ef1cebe7aeddf2dda31c996bf04`;
- Kissat, commit `8af8e56f174b778aef3aa45af9f739b2a5f492c2`.

Both projects are distributed under the MIT License. Their source and binaries
are stored under the ignored `.tools/` directory and are not included in this
repository.

## Optional OR-Tools Environment

`tools/bootstrap_ortools.sh` installs the hash-locked Python packages listed
in `tools/ortools-requirements.lock` under the ignored `.tools/` directory.
The Linux CI environment uses `tools/ortools-ci-requirements.lock`. OR-Tools
is distributed under the Apache License 2.0. The environments and their
installed packages are not included in this repository.
