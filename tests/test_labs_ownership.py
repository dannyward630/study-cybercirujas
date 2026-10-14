"""`teach lab down` with an ownership token removes only what that token created.

Copilot review 5526160852 on #1: checking a container's identity and then
calling a name-based `lab down` are two operations, so a container that took
the name in between would be deleted. With TEACH_LAB_OWNER set, `lab up`
stamps the container with a label at creation and `lab down` resolves the name
to IDs carrying that label before removing anything.

These tests put a *foreign* container under the lab's name — the "replaced
between check and teardown" case — and run the real provider against it.
Needs Docker and an already-present debian:12 (never pulls); skipped otherwise.
"""
import os
import shutil
import subprocess
import unittest
from unittest import mock

from teach.core import labs

NAME = "teach-ownership-test"
IMAGE = "debian:12"


def docker_ready() -> bool:
    if not shutil.which("docker"):
        return False
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return False
    return subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode == 0


class OwnerLabelTests(unittest.TestCase):
    def test_no_token_no_label(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TEACH_LAB_OWNER", None)
            self.assertEqual(labs._owner_label(), [])

    def test_token_becomes_a_label(self):
        with mock.patch.dict(os.environ, {"TEACH_LAB_OWNER": "run-1"}):
            self.assertEqual(labs._owner_label(), ["--label", f"{labs.OWNER_LABEL}=run-1"])


@unittest.skipUnless(docker_ready(), f"needs Docker with {IMAGE} already present (never pulls)")
class OwnedTeardownTests(unittest.TestCase):
    def run_container(self, *labels):
        args = ["docker", "run", "-d", "--pull=never", "--name", NAME]
        for label in labels:
            args += ["--label", label]
        return subprocess.run([*args, IMAGE, "sleep", "600"], check=True,
                              capture_output=True, text=True).stdout.strip()

    def setUp(self):
        if subprocess.run(["docker", "inspect", NAME], capture_output=True).returncode == 0:
            self.skipTest(f"{NAME} already exists here; not touching it")
        self.ids = []

    def tearDown(self):
        for container_id in self.ids:
            subprocess.run(["docker", "rm", "-f", container_id], capture_output=True)

    def running(self, container_id):
        return subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", container_id],
                              capture_output=True, text=True).stdout.strip() == "true"

    def test_a_foreign_container_under_the_name_survives(self):
        # Someone else's container (no label, or another owner's) holds the name.
        self.ids.append(self.run_container(f"{labs.OWNER_LABEL}=someone-else"))
        with mock.patch.dict(os.environ, {"TEACH_LAB_OWNER": "this-run"}):
            labs._down_container(NAME)
        self.assertTrue(self.running(self.ids[0]))

    def test_our_container_is_removed(self):
        self.ids.append(self.run_container(f"{labs.OWNER_LABEL}=this-run"))
        with mock.patch.dict(os.environ, {"TEACH_LAB_OWNER": "this-run"}):
            labs._down_container(NAME)
        self.assertFalse(self.running(self.ids[0]))


if __name__ == "__main__":
    unittest.main()
