#!/usr/bin/env python3
r"""Run Lake with serial Lean processes and a configurable Lean memory guard.

Examples (from mitten-distance-lean; this script uses only the Python standard library)::

    python3 scripts/build_bounded.py \
        --root . build MittenDistance.M150.Distance
    python3 scripts/build_bounded.py \
        --root . env lean scripts/AxiomCheck.lean
    python3 scripts/build_bounded.py \
        --root . --memory-mb 4608 --threads 1 --dry-run build

The selected toolchain must already be installed. An overlay under
<checkout>/.lake/mitten-bounded redirects Lean to this launcher without modifying
the toolchain or project configuration. A shared file lock permits one Lean
process at a time, including when Lake schedules several jobs. Each invocation
appends timing, exit status, and peak RSS in bytes to lean-processes.jsonl in
that directory. Separate launcher invocations also serialize their Lake runs.

The memory setting is Lean's internal allocation guard, NOT a hard RSS limit;
the operating system may report higher resident memory. Native compilation
and other Lake subprocesses are outside this Lean-only guard. Use this script
consistently: it cannot serialize unrelated, unwrapped Lean or Lake processes.
Only macOS and Linux are supported. --dry-run creates/validates the overlay and
prints the command, but starts neither Lake nor Lean.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import sys
import tempfile
import time


def positive_int(value: str) -> int:
    """Read a positive memory or thread setting."""
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def run_lean(real_lean: str, arguments: list[str]) -> int:
    """Hold the shared lock until the guarded Lean subprocess exits."""
    state = Path(os.environ["MITTEN_BOUNDED_STATE"])
    memory = positive_int(os.environ["MITTEN_LEAN_MEMORY_MB"])
    threads = positive_int(os.environ["MITTEN_LEAN_THREADS"])
    command = [real_lean, "-M", str(memory), "-j", str(threads), *arguments]
    with (state / "lean.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        started = time.monotonic()
        # Inheriting the lock also keeps it held if this wrapper is terminated
        # before Lean exits. The child needs no knowledge of the descriptor.
        result = subprocess.run(command, pass_fds=(lock.fileno(),))
        peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        record = {
            "args": arguments,
            "real_lean": real_lean,
            "cwd": os.getcwd(),
            "memory_mb": memory,
            "threads": threads,
            "seconds": time.monotonic() - started,
            "returncode": result.returncode,
            "peak_rss_bytes": int(peak if sys.platform == "darwin" else peak * 1024),
        }
        with (state / "lean-processes.jsonl").open("a") as log:
            log.write(json.dumps(record) + "\n")
    return result.returncode


def link_entry(source: Path, destination: Path) -> None:
    """Create an overlay link without overwriting an unrelated entry."""
    if destination.is_symlink() and destination.readlink() == source:
        return
    if destination.exists() or destination.is_symlink():
        raise RuntimeError(f"Unexpected existing overlay entry: {destination}")
    destination.symlink_to(source, target_is_directory=source.is_dir())


def make_overlay(state: Path, real_lean: Path) -> Path:
    """Mirror the installed sysroot, replacing only its Lean executable."""
    sysroot = real_lean.parent.parent
    identity = hashlib.sha256(str(sysroot).encode()).hexdigest()[:16]
    overlay = state / ("sysroot-" + identity)
    overlay.mkdir(exist_ok=True)
    (overlay / "bin").mkdir(exist_ok=True)
    for source in sorted(sysroot.iterdir()):
        if source.name != "bin":
            link_entry(source, overlay / source.name)
    for source in sorted((sysroot / "bin").iterdir()):
        if source.name != "lean":
            link_entry(source, overlay / "bin" / source.name)
    invocation = [sys.executable, str(Path(__file__).resolve()),
                  "--wrapped-lean", str(real_lean)]
    wrapper = "#!/bin/sh\nexec " + shlex.join(invocation) + ' "$@"\n'
    with tempfile.NamedTemporaryFile("w", dir=overlay / "bin", delete=False) as file:
        temporary = Path(file.name)
        file.write(wrapper)
    temporary.chmod(0o755)
    temporary.replace(overlay / "bin" / "lean")
    return overlay


def main() -> int:
    """Resolve the local toolchain, prepare its overlay, and invoke Lake."""
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", required=True, type=Path, help="Lean project checkout")
    parser.add_argument("--memory-mb", type=positive_int, default=4608,
                        help="Lean's internal memory limit in MB (default: 4608)")
    parser.add_argument("--threads", type=positive_int, default=1,
                        help="workers per Lean process (default: 1)")
    parser.add_argument("--dry-run", action="store_true",
                        help="create the overlay and print the command without running it")
    parser.add_argument("lake_args", nargs=argparse.REMAINDER,
                        help="Lake arguments, for example: build, or env lean file.lean")
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    if not (root / "lean-toolchain").is_file():
        parser.error(f"No lean-toolchain found in {root}")
    lake_args = args.lake_args
    if lake_args[:1] == ["--"]:
        lake_args = lake_args[1:]
    if not lake_args:
        parser.error("provide a Lake action, for example build")
    # `elan which` resolves an installed toolchain without running Lean.
    located = subprocess.check_output(["elan", "which", "lean"], cwd=root, text=True)
    real_lean = Path(located.strip()).resolve(strict=True)
    lake = real_lean.with_name("lake")
    if not lake.is_file():
        raise RuntimeError(f"No Lake executable beside {real_lean}")
    state = root / ".lake" / "mitten-bounded"
    state.mkdir(parents=True, exist_ok=True)
    with (state / "lake.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        overlay = make_overlay(state, real_lean)
        # Lake's `env` command replaces PATH, so an explicit wrapper path is
        # necessary even though the sysroot override handles normal builds.
        for index in range(len(lake_args) - 1):
            if lake_args[index:index + 2] == ["env", "lean"]:
                lake_args[index + 1] = str(overlay / "bin" / "lean")
                break
        env = os.environ.copy()
        env.update({
            "LAKE_OVERRIDE_LEAN": "true",
            "LEAN_SYSROOT": str(overlay),
            "LEAN_NUM_THREADS": str(args.threads),
            "MITTEN_BOUNDED_STATE": str(state),
            "MITTEN_LEAN_MEMORY_MB": str(args.memory_mb),
            "MITTEN_LEAN_THREADS": str(args.threads),
        })
        command = [str(lake), *lake_args]
        if args.dry_run:
            print(f"Working directory: {root}")
            print(f"Toolchain overlay: {overlay}")
            print(f"Lean memory guard: {args.memory_mb} MB; threads: {args.threads}")
            print(f"Process log: {state / 'lean-processes.jsonl'}")
            print(shlex.join(command))
            return 0
        return subprocess.run(command, cwd=root, env=env,
                              pass_fds=(lock.fileno(),)).returncode


if __name__ == "__main__":
    try:
        if sys.argv[1:2] == ["--wrapped-lean"]:
            status = run_lean(sys.argv[2], sys.argv[3:])
        else:
            status = main()
        raise SystemExit(status if status >= 0 else 128 - status)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"build_bounded: {error}", file=sys.stderr)
        raise SystemExit(1) from error
