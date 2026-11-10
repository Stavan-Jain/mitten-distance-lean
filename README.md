# mitten-distance-lean

Kernel-checked Lean proofs of the non-abelian lifted-product mitten code
`[[150,30,10]]`, built on [QECLean](https://github.com/Stavan-Jain/QECLean).
The concrete code, distance proof, thirty logical-operator pairs, checked
certificates, and deterministic generators live together here.

## Dependency and build

QECLean is pinned to an exact commit in both `lakefile.toml` and
`lake-manifest.json`. Lean is pinned to `v4.30.0-rc2`, and the manifest locks
the transitive dependencies. QECLean supplies the stabilizer and homological
frameworks, the general lifted-product construction, and shared packed
arithmetic lemmas. This repository contains the concrete instance and its
certificate checking.

With [elan](https://github.com/leanprover/elan) installed:

```sh
git clone https://github.com/Stavan-Jain/mitten-distance-lean.git
cd mitten-distance-lean
lake exe cache get
python3 scripts/build_bounded.py --root . build
python3 scripts/build_bounded.py --root . env lean scripts/AxiomCheck.lean
python3 scripts/build_bounded.py --root . env lean scripts/PublicApi.lean
```

The cache command obtains matching dependency artifacts; the repository's
proofs are checked by the subsequent build. Avoid `lake update` unless
deliberately changing the pinned dependencies.

The launcher permits one Lean process at a time and defaults to one worker
with a 4608 MB Lean allocation guard. The guard is not a hard resident-memory
limit. Timings and peak resident memory are recorded in
`.lake/mitten-bounded/lean-processes.jsonl`. Do not run another build or an
editor-triggered Lean check alongside it. CI uses the same serial launcher
with an 8192 MB guard on its 16 GB Linux runner and provides swap space.
The Linux floor and logical-basis checks exceeded the 4608 MB local default;
the CI setting applies to the build, axiom audit, and public-API check.

## Public theorems

```lean
import MittenDistance.M150.Distance
import MittenDistance.M150.Logicals
import QEC.Stabilizer.Framework.Core.CodeNotation

open scoped Quantum.StabilizerGroup
open Quantum.Stabilizer.Homological.LP.M150

#check (mitten150StabilizerCodeWithDistance : Code[[150, 30, 10]])
#check m150StabilizerCodeWithLogicals
#print axioms m150StabilizerCode_hasCodeDistance_10
#print axioms mitten150StabilizerCodeWithDistance
#print axioms m150StabilizerCodeWithLogicals
```

The mathematical declaration namespaces are preserved from QECLean; the
import root is now `MittenDistance`. Both public packages use the same
canonical stabilizer code. The distance theorem has no remaining floor or
classifier hypotheses. The proof policy permits only `propext`,
`Classical.choice`, and `Quot.sound`, with no admitted proofs, compiler-trust
proof steps, or custom axioms.

## Reading the proof

- [Proof overview](MittenDistance/README.md): the chain complex, sparse
  reductions, and low-weight classification.
- [Distance](MittenDistance/M150/Distance.lean): unconditional distance ten
  and the packaged code.
- [Stabilizer packaging](MittenDistance/M150/StabilizerCode.lean) and
  [logical operators](MittenDistance/M150/Logicals.lean): dimensions and the
  thirty certified logical pairs.
- [Certificate soundness](MittenDistance/M150/PackedGridSweep.lean): packed
  checks connected to the original split predicate.
- [Generator instructions](scripts/mitten/README.md): reproduction and
  input provenance.

The lower bound classifies cycles of weight at most nine and proves that
they are boundaries. An explicit nontrivial logical operator of weight ten
provides the upper bound. Python proposes data; Lean proves its coverage,
checks every certificate, and derives the mathematical conclusions.

## Reproduction and verification

```sh
python3 -m pip install -r scripts/mitten/requirements.txt
python3 scripts/check_layout.py
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/mitten/generate.py --verify
```

The generator reproduces the instance, mask, census, classifier, and join
modules. It compares against checked-in files without changing them in
verification mode. Use `--force` to regenerate after editing an emitter or
input; never edit a generated Lean file directly.

CI runs these checks, builds every local module, audits all local and imported
QECLean declarations, and verifies the public code parameters and canonical
packaging.

## Provenance and measurements

The proof was extracted from QECLean commit
[`8a4566e`](https://github.com/Stavan-Jain/QECLean/commit/8a4566ea8e6d7b43d7722a98e772455d9870ca8d),
with generators from qec-lab commit
[`0757e9d`](https://github.com/Stavan-Jain/qec-lab/commit/0757e9dfe2eaabe4e71220fa8c41cb01a65af9e7).
[The module map](provenance/module-migration.json) records all 64 moved
modules. Proof definitions and bodies are preserved; imports, generated-file
banners, documentation, and build tooling are adapted to this repository.

[Original validation evidence](provenance/original-validation/) is preserved
unchanged as historical evidence. Its 479.65-second source-check measurement
and 4.47 GiB peak resident memory describe the 76 added modules at QECLean
commit `03a4023` in the old layout. They are not measurements of this standalone tree. The
five-minute added-build target was missed; the ten-minute added-module
fallback was met. The old whole-repository run's timeout and continuation
are recorded separately.

The first standalone source build on 2026-11-06 checked all 64 local modules
in 493.70 seconds, with 4.07 GiB peak resident memory and matching
dependency caches reused. The axiom audit and public-API checks passed.
[Standalone validation](provenance/standalone-validation.json) records source
hashes and per-module measurements separately from the historical evidence.

Licensed under [Apache 2.0](LICENSE); see [NOTICE](NOTICE).
