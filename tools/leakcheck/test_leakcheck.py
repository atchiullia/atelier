"""Tests for leakcheck. Run: python3 -m unittest discover -s tools/leakcheck -v

Fixtures that would look like leaks are built by concatenation or at runtime so this
file passes its own gate.
"""
import importlib.util
import os
import re
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "leakcheck.py"
_spec = importlib.util.spec_from_file_location("leakcheck", SCRIPT)
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)

ENV = {k: v for k, v in os.environ.items() if k != "ATELIER_LEAK_PATTERNS"}


def token():
    return "q" + uuid.uuid4().hex[:10]


class ScanLine(unittest.TestCase):
    def test_private_ip_is_flagged(self):
        self.assertEqual(lc.scan_line("ssh 10." + "1.2.3", [], []), ["PRIVATE-IP"])
        self.assertEqual(lc.scan_line("gw 192." + "168.0.1", [], []), ["PRIVATE-IP"])
        self.assertEqual(lc.scan_line("pod 172." + "16.4.9", [], []), ["PRIVATE-IP"])
        self.assertEqual(lc.scan_line("ts 100." + "64.1.1", [], []), ["PRIVATE-IP"])

    def test_public_and_documentation_ranges_pass(self):
        self.assertEqual(lc.scan_line("host 192.0.2.10", [], []), [])
        self.assertEqual(lc.scan_line("host 198.51.100.7", [], []), [])
        self.assertEqual(lc.scan_line("not private 172.15.0.1", [], []), [])
        self.assertEqual(lc.scan_line("version 1.10.1.2.3", [], []), [])

    def test_internal_hostnames(self):
        self.assertEqual(lc.scan_line("nas." + "lan", [], []), ["INTERNAL-HOST"])
        self.assertEqual(lc.scan_line("pi." + "home.arpa", [], []), ["INTERNAL-HOST"])
        self.assertEqual(lc.scan_line("svc.cluster.local", [], []), [])
        self.assertEqual(lc.scan_line("www.example.com", [], []), [])

    def test_leak_ok_marker_skips_line(self):
        self.assertEqual(lc.scan_line("10." + "0.0.1  # leak-ok: fixture", [], []), [])

    def test_tier2_and_allow_list(self):
        tok = token()
        tier2 = [("T", re.compile(re.escape(tok), re.I))]
        allow = [re.compile(re.escape(tok) + "-public", re.I)]
        self.assertEqual(lc.scan_line(f"see {tok}", tier2, allow), ["T"])
        self.assertEqual(lc.scan_line(f"see {tok}-public", tier2, allow), [])
        self.assertEqual(lc.scan_line(f"see {tok.upper()}", tier2, allow), ["T"])


class CLI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "repo"
        self.root.mkdir()
        self.pdir = Path(self._tmp.name) / "patterns"
        self.pdir.mkdir()
        self.tok = token()
        (self.pdir / "patterns.txt").write_text(f"CANARY\t{self.tok}\n")
        self.git("init", "-q")

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                        "-c", "commit.gpgsign=false", *a],
                       cwd=self.root, check=True, capture_output=True)

    def run_lc(self, *a):
        return subprocess.run([sys.executable, "-I", str(SCRIPT), "--root", str(self.root), *a],
                              capture_output=True, text=True, env=ENV)

    def put(self, name, text):
        (self.root / name).write_text(text)

    def test_tracked_scan_is_redacted(self):
        self.put("a.txt", f"hello\nthe name is {self.tok}\n")
        self.git("add", "a.txt")
        r = self.run_lc("--patterns", str(self.pdir))
        self.assertEqual(r.returncode, 1)
        self.assertIn("LEAK CANARY a.txt:2", r.stdout)
        self.assertNotIn(self.tok, r.stdout + r.stderr)

    def test_clean_repo_passes(self):
        self.put("a.txt", "nothing to see\n")
        self.git("add", "a.txt")
        self.assertEqual(self.run_lc("--patterns", str(self.pdir)).returncode, 0)

    def test_fails_closed_without_patterns_in_ci_mode(self):
        self.assertEqual(self.run_lc("--require-patterns").returncode, 2)

    def test_fails_closed_on_missing_directory(self):
        self.assertEqual(self.run_lc("--patterns", str(self.pdir / "nope")).returncode, 2)

    def test_fails_closed_on_empty_pattern_file(self):
        (self.pdir / "patterns.txt").write_text("# only comments\n")
        self.assertEqual(self.run_lc("--patterns", str(self.pdir)).returncode, 2)

    def test_invalid_regex_fails_closed_without_echoing_it(self):
        (self.pdir / "manual.txt").write_text("BAD\t(unclosed\n")
        r = self.run_lc("--patterns", str(self.pdir))
        self.assertEqual(r.returncode, 2)
        self.assertNotIn("(unclosed", r.stdout + r.stderr)

    def test_space_instead_of_tab_fails_closed(self):
        (self.pdir / "manual.txt").write_text("BAD not-a-tab\n")
        self.assertEqual(self.run_lc("--patterns", str(self.pdir)).returncode, 2)

    def test_staged_mode_reads_the_index_not_the_working_tree(self):
        self.put("a.txt", "clean\n")
        self.git("add", "a.txt")
        self.put("a.txt", f"clean\n{self.tok}\n")            # unstaged edit
        self.assertEqual(self.run_lc("--staged", "--patterns", str(self.pdir)).returncode, 0)
        self.git("add", "a.txt")                              # now staged
        r = self.run_lc("--staged", "--patterns", str(self.pdir))
        self.assertEqual(r.returncode, 1)
        self.assertNotIn(self.tok, r.stdout + r.stderr)

    def test_history_finds_a_leak_that_was_later_removed(self):
        self.put("a.txt", f"{self.tok}\n")
        self.git("add", "a.txt")
        self.git("commit", "-q", "-m", "oops")
        self.put("a.txt", "fixed\n")
        self.git("commit", "-q", "-am", "remove")
        self.assertEqual(self.run_lc("--patterns", str(self.pdir)).returncode, 0)   # working tree is clean
        r = self.run_lc("--history", "--patterns", str(self.pdir))                  # history is not
        self.assertEqual(r.returncode, 1)
        self.assertRegex(r.stdout, r"LEAK CANARY [0-9a-f]+ a\.txt:1")
        self.assertNotIn(self.tok, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
