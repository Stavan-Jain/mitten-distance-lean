#!/usr/bin/env python3
"""Reproduce the mitten Lean certificates from pinned, checked-in inputs."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

PACKAGE = Path(__file__).resolve().parent
REPO = PACKAGE.parents[1]
OUTPUT = Path("MittenDistance/M150")
OWNER = "mitten-distance-lean:scripts/mitten/"
MANIFEST = PACKAGE / "output-manifest.json"


def verify_inputs(package: Path = PACKAGE) -> list[dict]:
    """Reject changed or duplicated certificate inputs before generation."""
    records = json.loads((package / "input-manifest.json").read_text())["inputs"]
    seen = set()
    for item in records:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts or str(relative) in seen:
            raise RuntimeError(f"Invalid or duplicate input path: {relative}")
        seen.add(str(relative))
        digest = hashlib.sha256((package / relative).read_bytes()).hexdigest()
        if digest != item["sha256"]:
            raise RuntimeError(f"Certificate digest mismatch: {relative}")
    return records


def check_owned(path: Path) -> None:
    """Refuse to overwrite files outside this generator family's ownership."""
    if path.exists():
        banner = path.read_text()[:1024]
        if "GENERATED FILE" not in banner or OWNER not in banner:
            raise RuntimeError(f"Refusing to replace an unrelated file: {path}")


def run_emitter(script: str, *args: object) -> None:
    """Run an emitter, retaining its detailed diagnostics if it fails."""
    command = [sys.executable, str(PACKAGE / script), *map(str, args)]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        sys.stderr.write(result.stdout + result.stderr)
        raise RuntimeError(f"Emitter failed: {script}")
    print(f"Completed {script}", flush=True)


def generate(stage: Path) -> list[Path]:
    """Build every generated module in an isolated staging directory."""
    output = stage / OUTPUT
    output.mkdir(parents=True)
    for mode in ("instance", "m4"):
        run_emitter("generate_data.py", mode, "--out", output, "--force")
    run_emitter("generate_joins.py", "--data", PACKAGE / "inputs/m4_triples.json",
                "--out", output, "--force")
    run_emitter("generate_sweeps.py", "--root", stage, "--all", "--force")
    sweep = json.loads((output / "sweep-manifest.json").read_text())
    outputs = [OUTPUT / name for name in
               ["Data.lean", "FloorData.lean", "JoinX.lean", "JoinZ.lean",
                *sweep["generated_sha256"], "sweep-manifest.json"]]
    if len(outputs) != len(set(outputs)):
        raise RuntimeError("Duplicate generated output")
    return sorted(outputs)


def output_manifest(stage: Path, outputs: list[Path]) -> str:
    """Record the exact generated artifacts for reproducible review."""
    data = {
        "generator": "scripts/mitten/generate.py",
        "input_manifest": "scripts/mitten/input-manifest.json",
        "generated_sha256": {
            str(path): hashlib.sha256((stage / path).read_bytes()).hexdigest()
            for path in outputs
        },
    }
    return json.dumps(data, indent=2) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", "--repo-root", type=Path, default=REPO)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--verify", action="store_true",
                      help="Compare regenerated artifacts without changing source files.")
    mode.add_argument("--force", action="store_true",
                      help="Replace this generator's existing artifacts.")
    parser.add_argument("--stage", type=Path,
                        help="Keep intermediate artifacts in a fresh staging directory.")
    args = parser.parse_args()
    root = args.root.resolve()
    if not (root / "MittenDistance").is_dir():
        parser.error(f"mitten-distance-lean checkout not found: {root}")
    inputs = verify_inputs()
    temporary = None
    if args.stage:
        stage = args.stage.resolve()
        if stage.exists():
            parser.error("Staging directory already exists; choose a fresh directory.")
        stage.mkdir(parents=True)
    else:
        temporary = tempfile.TemporaryDirectory(prefix="mitten-certificates-")
        stage = Path(temporary.name)
    try:
        outputs = generate(stage)
        manifest = output_manifest(stage, outputs)
        mismatches = []
        if args.verify:
            for relative in outputs:
                target = root / relative
                if not target.exists() or target.read_bytes() != (stage / relative).read_bytes():
                    mismatches.append(str(relative))
            target_manifest = root / "scripts/mitten/output-manifest.json"
            if not target_manifest.exists() or target_manifest.read_text() != manifest:
                mismatches.append("scripts/mitten/output-manifest.json")
            if mismatches:
                raise RuntimeError("Regeneration mismatch:\n" + "\n".join(mismatches))
        else:
            for relative in outputs:
                target = root / relative
                if target.exists() and not args.force:
                    parser.error(f"Generated file exists: {relative}; use --force.")
                if target.suffix == ".lean":
                    check_owned(target)
            for relative in outputs:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(stage / relative, target)
            target_manifest = root / "scripts/mitten/output-manifest.json"
            target_manifest.parent.mkdir(parents=True, exist_ok=True)
            target_manifest.write_text(manifest)
        action = "Verified" if args.verify else "Generated"
        print(f"{action} {sum(p.suffix == '.lean' for p in outputs)} Lean modules "
              f"and their manifests from {len(inputs)} hashed certificate inputs.")
    finally:
        if temporary is not None:
            temporary.cleanup()


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        raise SystemExit(str(error)) from error
