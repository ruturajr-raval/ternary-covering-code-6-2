# Third-Party Notices

## Reference 17-Word Code

`data/reference_17_code.txt` is transcribed from the explicit
`K_3(6,2) <= 17` certificate in `florath/covering-codes-lean`.

- Source:
  https://github.com/florath/covering-codes-lean/blob/main/CoveringCodes/Database/Sources/SmallExplicitUpper/K_3_6_2.lean
- Project license: BSD 3-Clause
- Copyright notice: retained by the upstream project and its contributors

The fixture is used only to test the independent verifier and search tools.
No upstream implementation code is included here.

## Optional SAT Solvers

`tools/bootstrap_solvers.sh` downloads and builds pinned revisions of:

- CaDiCaL, commit `c60730422e758ef1cebe7aeddf2dda31c996bf04`;
- Kissat, commit `8af8e56f174b778aef3aa45af9f739b2a5f492c2`.

Both projects are distributed under the MIT License. Their source and binaries
are stored under the ignored `.tools/` directory and are not included in this
repository.
