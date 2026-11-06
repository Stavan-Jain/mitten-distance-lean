# Mitten `[[150,30,10]]`

The mitten instance uses a lifted-product chain complex over `C₅ × S₃`.
Its distance argument classifies chains of weight at most nine, joins the
resulting block triples into stabilizer rows, and supplies an explicit
nontrivial logical operator of weight ten.

## Proof structure

- `M150/Defs.lean` and `Data.lean` specify the group-algebra instance and
  certificate data. QECLean's `Framework/Homological/LiftedProduct.lean`
  supplies the shared chain-complex construction.
- `Sparse.lean` identifies the boundary maps with sparse entry formulas;
  `SparseSupport.lean` evaluates chains from their listed support.
- `StabilizerCode.lean` checks inverse-matrix certificates and uses the
  shared homological presentation to construct the canonical
  `StabilizerCode 150 30`. `Logicals.lean` and `Witness.lean` describe the
  logical operators and the weight-ten witness.
- `FloorCore.lean` proves mask enumeration and split-checker soundness.
  `FloorBridge.lean` reuses `F2Mask` to connect masks to chains.
  `FloorChecksX.lean` and `FloorChecksZ.lean` check the finite map identities
  and census-to-row correspondence after symbolic sparse reductions.
- `PackedSweep.lean`, `PackedClassification.lean`, and `SweepAdapters.lean`
  connect packed arithmetic certificates to the split checker.
  `PackedGridSweep.lean` checks rectangular batches of mask pairs through
  the shared `PackedGrid` broadcasting identities. The shared
  `PackedPopcount32` specialization counts each thirty-bit mask in its
  own thirty-two-bit lane using five pair-summing stages. `MaskEnumeration`
  combines small mask-enumeration certificates into a symbolic coverage
  tree. Generated `MaskChunks`, `SweepMaps`, and `ClassifierParts` modules
  supply instance data. Independent parts and synchronous elaboration
  limit the amount of proof state retained during certificate checking.
  `CensusTables` checks ninety-bit packed copies of the four census lists,
  allowing direct bit lookups for the exceptional pairs.
  Elaboration assembles their limbs into numerals; separate kernel proofs
  check those numerals against the original lists. List packing uses
  shifts with a proved equivalence to `Nat.ofDigits`. The checker also
  packs input masks for direct lookup, preserving the lists' zero default
  outside their bounds, and skips these lookups for empty certificates.
  `GroupedJoin.lean` groups matching shared blocks; `JoinX.lean` and
  `JoinZ.lean` connect the resulting pairs to physical stabilizer rows.
- `FloorXSide.lean` and `FloorZSide.lean` expose the classification inputs as
  named hypotheses of `floorX_of_certificates` and
  `floorZ_of_certificates`. `Distance.lean` transfers chain floors to code
  distance and combines them with the explicit witness.

All four classification sweeps are kernel-checked. `Distance.lean` exposes
the unconditional `m150StabilizerCode_hasCodeDistance_10` and
`mitten150StabilizerCodeWithDistance : StabilizerCodeWithDistance 150 30 10`.
`Logicals.lean` supplies the thirty logical-operator pairs for the same
canonical stabilizer code.

## Provenance

The instance, census, and symbolic floor arguments come from
`claude/a32-lifted-product` at `2440ec8`. The parallel `[[360,12,24]]`
formalization on `codex/bravyi360-distance` supplied the packed arithmetic
approach: its reusable certificate modules were taken from `4d5ac9e`
(branch head `88ffe0a`) and placed under
`QEC/Stabilizer/Framework/Homological/Certificate/`. These general modules
remain in the pinned QECLean dependency. Mitten imports the canonical packed
digits, popcount, equality flags, and reconstruction lemmas from there.

The concrete proof was extracted from QECLean `8a4566e` into this repository.
Only the import root changed to `MittenDistance`; mathematical declaration
namespaces and proof bodies were preserved. The migration map under
`provenance/` records the moved modules and their source hashes.

## Regeneration

The self-contained generators and their required inputs live under
`scripts/mitten/` in this repository. From the repository root, run:

```sh
python3 -m pip install -r scripts/mitten/requirements.txt
python3 scripts/mitten/generate.py --verify
```

Verification regenerates the certificates separately and compares them with
the checked-in files. To replace generated files after editing an emitter or
input, run `python3 scripts/mitten/generate.py --force`. No qec-lab checkout
is needed. See `scripts/mitten/README.md` for the input manifest and generator
stages.

Generated Lean files carry a banner naming their generator. Change the
emitter and regenerate rather than editing those declarations. Commit the
emitter, input, and generated-output changes together.

## Building with bounded memory

From this repository root:

```sh
python3 scripts/build_bounded.py --root . build
python3 scripts/build_bounded.py --root . env lean scripts/AxiomCheck.lean
python3 scripts/build_bounded.py --root . env lean scripts/PublicApi.lean
```

The standard-library-only launcher serializes Lean processes and defaults
to one worker and a 4608 MB Lean allocation guard. The guard is not a hard
limit on resident memory. Timing and peak resident-memory measurements are
recorded under `.lake/mitten-bounded/lean-processes.jsonl`. Avoid running
another build or an editor-triggered Lean check alongside it.

## Historical validation

The 2026-11-06 source rebuild at QECLean `03a4023` checked all 76 added Lean
modules in 479.65 seconds of serial Lean time, with 4.47 GiB peak resident
memory. This missed the five-minute target but met the ten-minute fallback
for the added modules. The whole affected-repository rebuild reached a
600-second runner timeout after completing the port; the remaining existing
imports completed in a 21.93-second continuation. These measurements describe
the old QECLean layout, not the standalone package or an uninterrupted
whole-repository build.

That validation passed the full library, `QECLight`, `QECBlueprint`,
`QECWidgets`, `Playground.lean`, and umbrella checks. Its repository-wide
axiom audit checked 17,494 declarations across 272 modules and found only
the three standard axioms. A later integration check after updating QECLean
main passed the axiom audit for 15,528 declarations across 261 modules; the
smaller count reflects the extraction of the BB case studies.

Historical records are preserved under `provenance/original-validation/`.
Current CI separately builds and audits this repository's full import tree,
checks the public parameters, and verifies certificate regeneration.

## Trust policy

Generators propose certificate data; Lean proves the coverage, map
identities, packed checks, and their mathematical consequences. All proof
dependencies must be among `propext`, `Classical.choice`, and `Quot.sound`,
as required by the repository's axiom policy in `AGENTS.md`. Use
`#print axioms` on the floor and distance capstones and run
`python3 scripts/build_bounded.py --root . env lean scripts/AxiomCheck.lean`
after a completed build. Any unproved input must remain an explicit named
theorem hypothesis.
