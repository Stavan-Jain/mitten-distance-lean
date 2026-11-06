"""Regression tests for certificate input integrity and output ownership."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parent / "mitten"
spec = importlib.util.spec_from_file_location("mitten_generate", PACKAGE / "generate.py")
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class GeneratorSafetyTests(unittest.TestCase):
    def test_checked_in_inputs_are_pinned(self):
        self.assertEqual(len(generator.verify_inputs()), 3)

    def test_output_manifest_covers_exact_generated_modules(self):
        root = PACKAGE.parents[1]
        manifest = json.loads((PACKAGE / "output-manifest.json").read_text())["generated_sha256"]
        expected = {str(path.relative_to(root))
                    for path in (root / "MittenDistance").rglob("*.lean")
                    if "GENERATED FILE" in path.read_text()[:1024]}
        emitted = {path for path in manifest if path.endswith(".lean")}
        self.assertEqual(len(emitted), 43)
        self.assertEqual(emitted, expected)
        for path, digest in manifest.items():
            self.assertEqual(hashlib.sha256((root / path).read_bytes()).hexdigest(), digest)

    def test_modified_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input.json").write_text("original")
            digest = hashlib.sha256(b"original").hexdigest()
            (root / "input-manifest.json").write_text(json.dumps({
                "inputs": [{"path": "input.json", "sha256": digest}]}))
            generator.verify_inputs(root)
            (root / "input.json").write_text("changed")
            with self.assertRaisesRegex(RuntimeError, "digest mismatch"):
                generator.verify_inputs(root)

    def test_duplicate_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "input.json").write_bytes(b"input")
            item = {"path": "input.json", "sha256": hashlib.sha256(b"input").hexdigest()}
            (root / "input-manifest.json").write_text(json.dumps({"inputs": [item, item]}))
            with self.assertRaisesRegex(RuntimeError, "duplicate input"):
                generator.verify_inputs(root)

    def test_force_guard_preserves_unrelated_sources(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "Data.lean"
            path.write_text("theorem unrelated : True := True.intro\n")
            with self.assertRaisesRegex(RuntimeError, "unrelated file"):
                generator.check_owned(path)
            self.assertIn("unrelated", path.read_text())
            path.write_text("/- GENERATED FILE\nGenerator: " + generator.OWNER +
                            "generate_data.py\n-/\n")
            generator.check_owned(path)


if __name__ == "__main__":
    unittest.main()
