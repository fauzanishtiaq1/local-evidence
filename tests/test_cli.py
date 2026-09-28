import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

def run(*args):
    return subprocess.run([sys.executable, "-m", "local_evidence", *map(str, args)], cwd=ROOT, text=True, encoding="utf-8", capture_output=True)

class CliTests(unittest.TestCase):
    def test_build_search_stats_and_help(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td); source = tmp / "notes with spaces Ω"; source.mkdir(); doc = source / "design.md"
            doc.write_text("intro\nBM25 retrieval preserves exact citations\nclosing\n", encoding="utf-8"); index = tmp / "index Ω"
            p = run("build", source, index); self.assertEqual(p.returncode, 0, p.stderr); self.assertEqual(p.stderr, "")
            self.assertEqual(json.loads(p.stdout)["files"], 1)
            p = run("search", index, "BM25"); self.assertEqual(p.returncode, 0, p.stderr)
            hit = json.loads(p.stdout)[0]; self.assertEqual(hit["path"], "design.md"); self.assertEqual((hit["start_line"], hit["end_line"]), (1, 3)); self.assertIn("exact citations", hit["text"])
            p = run("stats", index); self.assertEqual(p.returncode, 0); self.assertEqual(json.loads(p.stdout)["files"], 1)
            for command in ("build", "search", "inspect", "stats"):
                p = run(command, "--help"); self.assertEqual(p.returncode, 0); self.assertTrue(p.stdout.startswith("usage:"))

    def test_inspect_rejects_changed_source_and_bad_args(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td); source = tmp / "src"; source.mkdir(); doc = source / "unicode Ω.txt"; doc.write_text("one\ntwo\nthree\n", encoding="utf-8"); index = tmp / "idx"
            self.assertEqual(run("build", source, index).returncode, 0)
            p = run("inspect", index, "unicode Ω.txt", "--start-line", 1, "--end-line", 2); self.assertEqual(p.returncode, 0, p.stderr); self.assertEqual(json.loads(p.stdout)["text"], "one\ntwo")
            doc.write_text("changed\ntwo\nthree\n", encoding="utf-8"); p = run("inspect", index, "unicode Ω.txt", "--start-line", 1, "--end-line", 2); self.assertEqual(p.returncode, 1); self.assertEqual(p.stdout, "")
            self.assertEqual(run("search", index, "").returncode, 2); self.assertEqual(run("search", index, "x", "--top-k", 0).returncode, 2)
