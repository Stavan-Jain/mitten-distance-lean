# Build-time budget ledger — mitten_150_30_10

**Constraint (user, 2026-08-10): the certification adds ≤ 5 minutes to a
full QECLean `lake build`. Fallback ceiling 10 minutes — hard cap, never
exceeded.** Measured on the dev machine (Apple silicon, the same class
of box all program reference costs below come from). Wall clock of the
added modules; parallelism across independent files may be counted, but
each allocation below is written as if serial so parallel build is pure
margin.

## Kernel port (2026-11-04)

The current port replaces every compiler-trusted leaf with kernel-checked
certificates and symbolic proofs. Only `propext`, `Classical.choice`, and
`Quot.sound` are permitted. The historical measurements below describe the
parked implementation and do not validate the new port. The five-minute
target and ten-minute ceiling remain in force. The 2026-11-06 measurement below
meets the added-module fallback; the five-minute target remains missed.

The certificate checker borrows the packed arithmetic approach from the
parallel `[[360,12,24]]` formalization. It uses 32-bit lanes for the mitten
code's 30-bit masks, broadcasts rectangular blocks of candidate pairs, and
checks census membership through explicit indices. Joins group triples by
their common block before checking the remaining pairs.

## Historical allocations (target tier: 5 min = 300 s)

| Layer | Files | Allocation | Notes |
|---|---|---:|---|
| M1 framework | `LiftedProduct.lean` | 10 s | pure proofs |
| M2 data | `M150/Data.lean` (generated) | 20 s | packed-Nat literals; elaboration only |
| M2 packaging | `M150/{Defs,StabilizerCode}.lean` | 40 s | 2 decoder identities ≈ 5–10 s each (gross analog: ~5 s at 72×144); rest batched |
| M3 witness | `M150/Witness.lean` | 10 s | kernel `decide` |
| M4 floor, ker-H_X side | `M150/FloorZSide*.lean` | 90 s | certificates + ≤ 2 batched native leaves |
| M4 floor, ker-H_Z side | `M150/FloorXSide*.lean` | 90 s | same shape, independent files (parallel margin) |
| M5 assembly | `M150/Distance.lean`, umbrella | 20 s | transport + bundle |
| **Total** | | **280 s** | 20 s slack at the 5-min tier |

The 10-minute fallback, if invoked, is spent **only** on the M4 lines
(→ 240 s/side); every other allocation is firm.

## Reference costs (program history, same machine class)

| Fact | Cost | Lesson |
|---|---:|---|
| A15 sweep layer as filter-form `native_decide` masks (~560 M) | 53 min | banned form |
| Same layer as Gaussian-pivot certificates (`KernelCert` + emitter v3) | 3.9 s | mandatory form |
| Gross decoder identity (72×144, one `native_decide`) | ~5 s | M2 model |
| Z3Z6 bitmask-reworked sweep (per sweep, statement-identical) | ~84 s | ceiling for ONE residual leaf |
| Packed-Nat table walk (RBlock, was 24 min naive) | 0.4 s | table discipline |
| `native_decide` fixed overhead per invocation | ~1–3 s | batch; prefer kernel `decide` under ~1 s |

## Binding design rules

1. Python proposes data; Lean proves coverage and checks every certificate.
2. No `native_decide`, `sorry`, or custom axioms in library proofs. Audit the
   final public declarations and run the repository-wide axiom check.
3. Use symbolic identities to reduce finite checks to sparse tables and
   packed arithmetic; avoid re-enumerating full matrix sums in the kernel.
4. Keep certificate modules independent where possible so the build can
   check them concurrently.
5. Measure the full added-source build. Above 300 seconds, report the target
   miss; above 600 seconds, do not merge the implementation.

## Measured ledger

### Kernel-only port validation (2026-11-06)

The unconditional distance theorem and logical basis now pass kernel checking.
All 76 added Lean modules were rebuilt from source with dependencies cached,
one Lean process at a time, one worker, and a 4608 MB Lean allocation guard.
The guard is not a hard limit on resident memory.

| Measurement | Result |
|---|---:|
| Added-module serial Lean time | 479.65 s |
| Peak resident memory | 4.47 GiB |
| Five-minute added-build target | Missed |
| Ten-minute added-module fallback | Met |
| Whole affected-repository run | Timed out at 600.07 s, after the port completed |
| Continuation of remaining existing imports | Passed in 21.93 s |

The whole-repository run includes existing downstream modules rebuilt after
the framework imports changed. It is not interchangeable with the added-module
measurement, and no uninterrupted whole-repository build under 600 seconds is
claimed. Both the timeout and continuation are retained in
`kernel_build_measurement.json`, alongside per-module measurements and source
hashes.

The full library, light import surface, blueprint target, widget target,
Playground, and umbrella checks pass. The repository-wide axiom audit passes
for 17,494 declarations across 272 modules with only `propext`,
`Classical.choice`, and `Quot.sound`. The final capstones have no remaining
floor or classifier hypotheses.

The final certificates use 24 independent classifier parts, 380 splits,
1,241 grids, 104 small mask-enumeration leaves, and four packed censuses.
Packed input/census lookups avoid repeated list traversal; shift-based packing
avoids multiplication by wide powers of two. Generators and elaboration propose
data, while independent kernel proofs verify it.

Reproduce the bounded build with
`experiments/bb_lab/scripts/mitten_kernel/build_bounded.py --root <QECLean> build`.
The detailed historical native-check measurements below are preserved as
history and do not describe the kernel-only port.

| Date | File | Wall (s) | Method | Notes |
|---|---|---:|---|---|
| 2026-08-10 | (probe) `A32Baseline.lean` | 3.2 | `lake env lean`, warm | imports only (Dihedral + ZMod + Fintype.Prod) |
| 2026-08-10 | (probe) `A32Rehearsal.lean` | 12.4 | `lake env lean`, warm | **delta ≈ 9.2 s** for R1–R4 together (see below) |
| 2026-08-10 | `Framework/Homological/LiftedProduct.lean` (M1) | 8.3 | `lake build`, worktree `claude/a32-lifted-product` @ 3b9a4b8 | pure proofs; warning-free; vs 10 s allocation |
| 2026-08-10 | `Codes/Mitten/M150/Data.lean` (M2 data, generated) | 3.0 | `lake build` @ 7842caf | packed tables; vs 20 s allocation |
| 2026-08-10 | `Codes/Mitten/M150/Defs.lean` (M2) | 2.3 | `lake build` @ 7842caf | indicator polys + complex + decides |
| 2026-08-10 | `Codes/Mitten/M150/StabilizerCode.lean` (M2 packaging) | 19.0 | `lake build` @ 64da329, twice (fresh + forced re-elab) | 7 natives: 2 pointwise entry bridges (9000 cells), 2 decoder identities (3600×60), 3 logical-basis facts (cycles/dual-cycles/inner 30×30); packaging line total w/ Defs = 21.3 s vs 40 s allocation |
| 2026-08-10 | `Codes/Mitten/M150/Witness.lean` (M3) | 1.7 | `lake build` @ 64da329 | ONE batched native (4 conjuncts); vs 10 s allocation |
| 2026-08-10 | `Framework/Homological/LogicalCorrespondence.lean` (edit) | ~0 | — | +15-line mirror lemma `not_mem_dualBoundaries_of_witness` in a pre-existing module; not an added module, no measurable delta |
| 2026-08-11 | (probe) `A32M4Probe.lean` | 7.3 | `lake env lean`, warm | M4 rehearsal: FULL X0 instance sweep (95 splits, 8.57M classes, 3 modes, 1,995-triple classification) as ONE native_decide; naive driver was 69 s — fold-hoisting + SWAR popcount gave 9.4× (final driver uses a 15-bit table popcount: 6.4 s, and it is correct-by-construction) |
| 2026-08-11 | `Codes/Mitten/M150/FloorCore.lean` (M4 core) | 2.4 | `lake build`, forced re-elab | generic mask/sweep layer, fully symbolic (no natives) |
| 2026-08-11 | `Codes/Mitten/M150/FloorData.lean` (M4 data, generated) | 14.0 | `lake build` | ~700 KB packed tables/lists; elaboration only |
| 2026-08-11 | `Codes/Mitten/M150/FloorSweepX.lean` (M4 leaf) | 15.0 | `lake build` | 3 natives: X0+X1 sweeps + X join |
| 2026-08-11 | `Codes/Mitten/M150/FloorSweepZ.lean` (M4 leaf) | 40.0 | `lake build` | 3 natives: Z0+Z1 sweeps + Z join; identity-tP fold overhead on unique-u splits noted |

### Final certification measurement (2026-08-11, M4 plumbing + M5 landed)

One forced full re-elaboration of every certification module (deleted
`.olean`/`.ilean` under `.lake/build/lib/lean/`, one `lake build
QEC.Stabilizer.Codes.Mitten`), per-module walls from lake:

| Module | Wall (s) | Notes |
|---|---:|---|
| `Framework/Homological/LiftedProduct.lean` | 2.9 | M1 |
| `M150/FloorCore.lean` | 3.3 | + linear_pred, parity functionals, composite transfer, checkJoin_sound, pack5 extraction |
| `M150/Data.lean` | 2.2 | M2 data |
| `M150/Defs.lean` | 1.9 | M2 |
| `M150/FloorData.lean` | 6.7 | regenerated + 6 bridge tables (tRawAX, tCinvX0/1, tRawCZ0/1, tAinvZ) |
| `M150/FloorSweepX.lean` | 14.0 | 3 natives (unchanged) |
| `M150/StabilizerCode.lean` | 23.0 | M2 packaging (unchanged) |
| `M150/Witness.lean` | 3.6 | M3 (unchanged) |
| `M150/FloorBridge.lean` | 3.0 | NEW: maskOf/comask, maskOf_op transfer, entrySum block maps, weight bridges — symbolic only |
| `M150/FloorZSide.lean` | 11.0 | NEW: 2 natives (basis bridge, census/rows) + ~30 kernel decides + floorZ |
| `M150/FloorSweepZ.lean` | 41.0 | 3 natives (unchanged) |
| `M150/FloorXSide.lean` | 10.0 | NEW: mirror leaf + floorX |
| `M150/Distance.lean` | 1.7 | NEW: M5 transfer + witness + bundle |
| `Codes/Mitten.lean` umbrella | 1.5 | |
| **Serial total** | **125.8** | **wall-clock 67.5 s at 229% CPU (lake parallelism)** |

**Measured total (library files): 125.8 s serial / 300 s cap — CLOSED at
42% of budget** (67.5 s wall on the dev machine; the M4 allocation used
89.0 s of its 180 s line, M5 used 1.7 s of 30 s).  Axiom audit on the
bundle: `propext`, `Classical.choice`, `Quot.sound` + the 18
`native_decide` leaf axioms; no sorries.

Protocol note (2026-08-10): `touch` no longer forces lake rebuilds (lake
is content-hash-based on this toolchain) — measure by deleting the
module's `.olean`/`.ilean` under `.lake/build/lib/lean/` and rebuilding,
or take the per-module wall times lake prints on the first build.

### Budget rehearsal result (M0.4, 2026-08-10)

Emitted by `scripts/m150_gen_lean_data.py rehearsal` (falsify-first:
dictionary hom + closed-form H entries + pivot certificate all validated
in Python before emission; R1's in-Lean pass additionally proves the
mathlib `sr`-orientation is right — a sign error could not have passed).
One file, four representative obligations, **compiled clean on first
attempt**, all `native_decide`/`decide` returning true:

| Obligation | Shape | Scale |
|---|---|---|
| R1 `dict_hom` | native_decide, group products through `getD` tables | 900 products |
| R2 `hzRows_in_kerHX` + `hzRows_weight9` | native_decide, closed-form H entries, `Finset` sums | 540k + 9k terms |
| R3 `pivot_cert` | native_decide, packed-Nat `testBit` × closed-form H | 216k terms |
| R4 `gapElem_inj` | kernel `decide`, carrier comparisons | 900 pairs |

All four together ≈ 9.2 s — comfortably inside the M2 allocation (60 s)
for obligations of exactly this kind, with ~1–3 s of the delta being
per-`native_decide` compiler overhead (4 invocations; the batching rule
stands). Carrier arithmetic (`Multiplicative (ZMod 5) × DihedralGroup 3`)
is NOT a bottleneck at this size; the `DihedralGroup`-vs-`Fin 30`-table
fallback in plan.md's risk table is not needed. M4 leaf design can
assume: a certificate-shaped `native_decide` at 10⁵–10⁶ term scale ≈
seconds — the 180 s floor allocation buys O(20–40) such leaves, or a few
at 10⁷ scale.

**Measured total: 0 s / 300 s.**

## Measurement protocol

Use a fresh build directory with existing dependencies cached, or remove only
this port's module artifacts before rebuilding. Merely touching sources does
not invalidate Lake's content hashes. Measure one `lake build` with the mitten
umbrella enabled and record both wall time and peak memory. Keep other heavy
proof checks idle during the measurement.

Record wall + user CPU; once per phase also measure the cold delta of a
full `lake build` with and without the mitten umbrella imported from
`QEC.lean`.
