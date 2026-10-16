"""`make pr-check` exists, is wired to scripts/pr_check.py, and fails on a broken PR description.

Uses --fast (skips the ~90 s verify-ci block, which is the other tests' job),
so this adds about a second to the suite.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "pr_check.py"


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), "--fast", *args], cwd=REPO,
                          capture_output=True, text=True)


class PrCheckTests(unittest.TestCase):
    def test_targets_exist(self):
        for target in ("pr-check", "install-hooks", "uninstall-hooks"):
            made = subprocess.run(["make", "-n", target], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(made.returncode, 0, f"{target}: {made.stderr}")

    def test_pre_push_hook_is_inert_unless_opted_in(self):
        hook = (REPO / ".githooks" / "pre-push").read_text(encoding="utf-8")
        self.assertIn("pr-check.prepush", hook)
        self.assertIn("exit 0", hook)

    def test_a_broken_description_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp) / "body.md"
            body.write_text("## What and why\n\nnothing else\n", encoding="utf-8")
            out = run("--body-file", str(body), "--title", "not a conventional title")
        self.assertEqual(out.returncode, 1, out.stdout)
        self.assertRegex(out.stdout, r"FAIL\s+PR description")

    def test_without_a_description_it_only_warns(self):
        out = run()
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("WARN  PR description not checked", out.stdout)


if __name__ == "__main__":
    unittest.main()
