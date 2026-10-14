"""The e2e lab step never adopts or deletes a lab it did not create.

Review on #1: the EXIT trap of clone_and_run.sh ran `lab down` on the fixed
name `teach-lpi-010-160-2-1` even when that run had not created it, so a test
run could delete a student's lab and their work. tests/e2e/lab_step.sh now
refuses (exit 3) when the name is taken and only cleans up what it created.
This puts a container with that name in place first and checks it survives.
Needs Docker; skipped without it.
"""
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
NAME = "teach-lpi-010-160-2-1"


def docker_ready() -> bool:
    if not shutil.which("docker") or not shutil.which("bash"):
        return False
    return subprocess.run(["docker", "info"], capture_output=True).returncode == 0


@unittest.skipUnless(docker_ready(), "needs Docker")
class LabStepIsolationTests(unittest.TestCase):
    def setUp(self):
        existing = subprocess.run(["docker", "ps", "-a", "--format", "{{.Names}}"],
                                  capture_output=True, text=True).stdout.split()
        if NAME in existing:
            self.skipTest(f"{NAME} already exists on this machine; not touching it")
        subprocess.run(["docker", "run", "-d", "--name", NAME, "--label", "study-test=isolation",
                        "debian:12", "sleep", "600"], check=True, capture_output=True)

    def tearDown(self):
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)

    def test_an_existing_lab_is_left_alone(self):
        teach = Path(sys.executable).parent / "teach"
        result = subprocess.run(["bash", str(REPO / "tests" / "e2e" / "lab_step.sh"), str(REPO)],
                                capture_output=True, text=True, timeout=120,
                                env={**os.environ, "TEACH": str(teach)})
        self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
        self.assertIn("left untouched", result.stdout)
        state = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}} {{index .Config.Labels \"study-test\"}}",
                                NAME], capture_output=True, text=True).stdout.strip()
        self.assertEqual(state, "true isolation")


if __name__ == "__main__":
    unittest.main()
