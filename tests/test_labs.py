"""The local lab provider must hand the student's stdin to break_fix.sh.

Found by running `teach lab up lpi-010-160 2.1` on a clean clone (2026-10-14):
the script asks for a confirmation, `docker exec` had no `-i`, `read` got EOF,
the script cancelled itself and the lab was reported as running with nothing
broken. 178 of the 548 lab scripts ask for a confirmation this way.
"""
import unittest

from teach.core import labs


class ExecScriptCmdTests(unittest.TestCase):
    def test_stdin_is_attached(self):
        cmd = labs._exec_script_cmd("teach-x", interactive=False)
        self.assertIn("-i", cmd)
        self.assertNotIn("-t", cmd)  # docker refuses -t without a terminal

    def test_terminal_gets_a_tty(self):
        cmd = labs._exec_script_cmd("teach-x", interactive=True)
        self.assertEqual(cmd[:4], ["docker", "exec", "-i", "-t"])
        self.assertEqual(cmd[-3:], ["teach-x", "bash", "break_fix.sh"])


class EnterHintTests(unittest.TestCase):
    def test_container_lab_names_the_shell(self):
        hint = labs.enter_hint("lpi-010-160", "2.1")
        self.assertEqual(
            hint, "docker exec -it -u student -w /home/student teach-lpi-010-160-2-1 bash")


if __name__ == "__main__":
    unittest.main()
