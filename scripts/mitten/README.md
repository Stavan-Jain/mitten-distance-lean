# Mitten certificate generation

The generator reproduces 43 Lean modules under `MittenDistance/M150`, the
sweep manifest, and `scripts/mitten/output-manifest.json`. It uses Python 3.11
or newer and the NumPy version pinned in `requirements.txt`.

```sh
python3 -m pip install -r scripts/mitten/requirements.txt
python3 scripts/mitten/generate.py --verify
python3 -m unittest discover -s scripts -p 'test_*.py'
```

`--verify` generates into a temporary directory and compares every output
byte for byte. It leaves the checked-in files unchanged. To regenerate after
an intentional generator change:

```sh
python3 scripts/mitten/generate.py --force
```

Use `--root <checkout>` to select a different destination checkout, or
`--stage <fresh-directory>` to retain intermediate output for inspection.
The wrapper checks all input hashes before generation and refuses to overwrite
Lean files without this generator family's ownership banner.

## Inputs and provenance

`input-manifest.json` records hashes and original locations for:

- `inputs/group_30_1.txt`: GAP's multiplication, inverse, and order tables for
  `SmallGroup(30,1)` in the paper's element ordering.
- `inputs/m4_triples.json`: the four candidate triple censuses used by the
  finite classification proofs.
- `inputs/witness.json`: the existing weight-ten witness and its pairing,
  extracted from the verified QECLean `Data.lean` at commit `8a4566e`.

The manifest also identifies the original qec-lab emitter files and their
hashes. Production algebra and output order are preserved. The extraction
retargets imports and generated banners, removes the historical rehearsal
mode, and uses the pinned witness in place of running the original SAT search.
Every generated Lean body was compared with the original at `8a4566e` after
normalizing imports and the leading banner.

## Generator stages

1. `generate_data.py` validates the finite-group dictionary against the
   multiplication table, compares two constructions of the check matrices,
   computes inverse-matrix certificates and a symplectic logical basis, and
   checks the pinned witness and pairing. Its floor-data stage reproduces
   every table, split, and census and simulates the classification and joins.
2. `generate_joins.py` groups census triples by their shared block and emits
   certificates that grouping preserves the lists and all compatible pairs
   reconstruct stabilizer rows.
3. `generate_sweeps.py` emits recursive mask coverage, packed census tables,
   linear-map certificates, and all 380 classification splits. The default
   partition has 24 classifier parts and 1,241 grids. The sweep manifest
   records chunk sizes and hashes for its 39 outputs.

`group_model.py` contains only the group-table reader and direct matrix
construction required by the first stage. Regeneration requires no research
checkout or external solver. The complete output manifest includes all 43
Lean modules and `sweep-manifest.json`.

## Proof policy

Python supplies candidate data. Lean proves enumeration coverage and checker
soundness, verifies every finite certificate in the kernel, and derives the
unconditional distance theorem. Census completeness follows from those Lean
sweeps. The witness's nonboundary property follows from its checked pairing.

After regeneration, run the repository's bounded build, axiom audit, and
public-API checks as described in the root README. The permitted axioms are
`propext`, `Classical.choice`, and `Quot.sound`.
