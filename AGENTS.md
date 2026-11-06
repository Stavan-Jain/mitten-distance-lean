# mitten-distance-lean

This repository contains the concrete mitten `[[150,30,10]]` formalization,
its certificates, and deterministic generators. General theory lives in the
pinned QECLean dependency.

## Axiom policy

- Never use `sorry`, `native_decide`, or custom axioms in committed proofs.
  The allowed dependencies are `propext`, `Classical.choice`, and `Quot.sound`;
  declarations using fewer axioms are also allowed.
- Run `python3 scripts/build_bounded.py --root . env lean scripts/AxiomCheck.lean`
  and `#print axioms` on the public capstones.
- Preserve proof bodies verbatim when moving them, adapting imports and names.
- Add a `/-- ... -/` docstring to every new lemma and theorem. Wrap prose at
  80 columns and Lean code at 100 columns. Do not suppress linters.
- Reuse QECLean and mathlib APIs. Keep the derived presentation's stabilizer
  code as the single canonical code.

## Generation and builds

- Never hand-edit files marked `GENERATED FILE — DO NOT HAND-EDIT`. Change
  the emitters or inputs under `scripts/mitten/`, regenerate, and run
  `python3 scripts/mitten/generate.py --verify`.
- Keep every local Lean module reachable from `MittenDistance.lean` and run
  `python3 scripts/check_layout.py` after adding or moving modules.
- Use `python3 scripts/build_bounded.py --root . build` for Lean builds.
  It serializes Lean processes and uses one worker with a memory guard.
  Do not run another build or editor-triggered Lean process concurrently.
- Before publishing changes, run the full bounded build, `scripts/AxiomCheck.lean`,
  `scripts/PublicApi.lean`, layout checks, generator verification, and Python tests.
- Toolchain, QECLean commit, and transitive dependencies are pinned. Do not run
  `lake update`, fetch a new mathlib cache, or rebuild large fractions of mathlib
  without user authorization. Reuse matching cached dependencies when available.
- Preserve `provenance/original-validation/` as historical evidence; its
  measurements describe the old QECLean layout, not this standalone tree.
