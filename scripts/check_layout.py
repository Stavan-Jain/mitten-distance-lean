#!/usr/bin/env python3
"""Check import coverage, the pinned dependency, and the extraction boundary."""
from pathlib import Path
import json
import re
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    """Require a complete local import graph and a matching immutable QEC pin."""
    config = tomllib.loads((ROOT / "lakefile.toml").read_text())
    qec = next(p for p in config["require"] if p["name"] == "QEC")
    assert re.fullmatch(r"[0-9a-f]{40}", qec["rev"]), "QECLean needs a full commit SHA"
    manifest = json.loads((ROOT / "lake-manifest.json").read_text())
    locked = next(p for p in manifest["packages"] if p["name"] == "QEC")
    assert locked["rev"] == locked["inputRev"] == qec["rev"], "QECLean pins disagree"
    assert locked["url"] == qec["git"], "QECLean URLs disagree"
    migration = json.loads((ROOT / "provenance/module-migration.json").read_text())
    moved = {
        Path(row["target"]).with_suffix("").as_posix().replace("/", ".")
        for row in migration["modules"]
    }
    old = {
        Path(row["source"]).with_suffix("").as_posix().replace("/", ".")
        for row in migration["modules"]
    }
    local = {
        p.relative_to(ROOT).with_suffix("").as_posix().replace("/", "."): p
        for p in (ROOT / "MittenDistance").rglob("*.lean")
    }
    local["MittenDistance"] = ROOT / "MittenDistance.lean"
    visiting, seen = set(), set()

    def visit(module: str) -> None:
        assert module in local, f"Missing local module: {module}"
        assert module not in visiting, f"Import cycle: {module}"
        if module in seen:
            return
        visiting.add(module)
        source = local[module].read_text()
        for row in re.findall(r"^import (.+)$", source, re.M):
            for dependency in row.split():
                assert dependency not in old, f"Stale pre-extraction import: {dependency}"
                if dependency == "MittenDistance" or dependency.startswith("MittenDistance."):
                    visit(dependency)
        visiting.remove(module)
        seen.add(module)

    visit("MittenDistance")
    assert seen == set(local), f"Unreachable modules: {sorted(set(local) - seen)}"
    assert moved <= seen, f"Missing extracted modules: {sorted(moved - seen)}"
    assert not (ROOT / "QEC").exists(), "QECLean sources must remain a dependency"
    print(f"Layout OK: {len(local)} local modules; QECLean pinned to {qec['rev']}.")


if __name__ == "__main__":
    main()
