"""The guard's laws: switching a test off is refused unless the owner granted that exact finding,
and a credential anywhere in a push's history is refused whatever the mode or grant.

Run: python3 tests/test_guard_laws.py   (no network, no dependencies; builds throwaway repos)
"""
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "scripts" / "agent-check"
TOKEN = "gh" + "p_" + "A1b2" * 9  # a GitHub token shape, built so this file holds no literal credential

TEST_X = '''import unittest


class TestX(unittest.TestCase):
    def test_one(self):
        self.assertEqual(1 + 1, 2)

    def test_two(self):
        self.assertEqual(2 * 2, 4)
'''
TEST_A = "def test_a():\n    assert True\n"
TEST_JS = 'it("adds", () => {\n  expect(1 + 1).toBe(2);\n});\n'


def config(guard):
    return ('test = "true"\none_test = "true"\ntests = "tests/"\n\n[gates]\n'
            'laws = "off"\nred_first = "off"\nseals = "off"\nverified = "off"\n'
            f'evidence = "off"\nfresh = "off"\nguard = "{guard}"\n')


def sh(cwd, *cmd):
    run = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if run.returncode != 0:
        raise AssertionError(f"{cmd} failed: {run.stdout}{run.stderr}")
    return run


class Repo:
    """A throwaway repo with one base commit; `base` is the sha the push is checked from."""

    def __init__(self, guard="enforce"):
        self.dir = Path(tempfile.mkdtemp())
        sh(self.dir, "git", "init", "-q", "-b", "main")
        sh(self.dir, "git", "config", "user.name", "t")
        sh(self.dir, "git", "config", "user.email", "t@t")
        self.write("agent-check.toml", config(guard))
        self.write("tests/test_x.py", TEST_X)
        self.write("tests/test_a.py", TEST_A)
        self.write("tests/app.test.js", TEST_JS)
        self.commit("base")
        self.base = sh(self.dir, "git", "rev-parse", "HEAD").stdout.strip()

    def read(self, path):
        return (self.dir / path).read_text()

    def write(self, path, text):
        (self.dir / path).parent.mkdir(parents=True, exist_ok=True)
        (self.dir / path).write_text(text)

    def git(self, *args):
        return sh(self.dir, "git", *args)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)

    def push(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        return subprocess.run(["python3", str(TOOL), "push", "--base", self.base, "--no-suite"],
                              cwd=self.dir, capture_output=True, text=True, env=env)


def findings(stderr, rule, path=r"\S+?"):
    """The ids of every `[rule] path[:line] id=xxxxxxxx — what. Fix: how` line on stderr."""
    pattern = rf"\[{re.escape(rule)}\] {path}(?::\d+)? id=([0-9a-f]{{8}}) — .*Fix: \S"
    return re.findall(pattern, stderr)


class GuardLaws(unittest.TestCase):
    def refused(self, run, rule, path=r"\S+?"):
        self.assertEqual(run.returncode, 1, run.stderr)
        ids = findings(run.stderr, rule, path)
        self.assertTrue(ids, f"no [{rule}] finding in:\n{run.stderr}")
        return ids

    def skip_test_one(self, repo, marker='@unittest.skip("x")'):
        repo.write("tests/test_x.py", repo.read("tests/test_x.py").replace(
            "    def test_one", f"    {marker}\n    def test_one"))
        repo.commit("switch test_one off")

    # --- L1 ---
    def test_a_skip_marker_added_to_a_test_is_refused(self):
        """[L1] Under enforce, a unittest, pytest or JS skip marker added to a test is refused."""
        variants = {
            "unittest": ("tests/test_x.py", lambda t: t.replace("    def test_one", '    @unittest.skip("x")\n    def test_one')),
            "pytest": ("tests/test_x.py", lambda t: "import pytest\n" + t.replace("    def test_one", "    @pytest.mark.skip\n    def test_one")),
            "js": ("tests/app.test.js", lambda t: t.replace('it("adds"', 'it.skip("adds"')),
        }
        for name, (path, change) in variants.items():
            with self.subTest(name):
                repo = Repo()
                repo.write(path, change(repo.read(path)))
                repo.commit(f"skip via {name}")
                self.refused(repo.push(), "test-skipped", re.escape(path))

    def test_a_deleted_test_file_is_refused(self):
        """[L1] Under enforce, deleting a test file is refused."""
        repo = Repo()
        repo.git("rm", "-q", "tests/test_a.py")
        repo.commit("delete a test file")
        self.refused(repo.push(), "test-deleted", re.escape("tests/test_a.py"))

    def test_a_test_file_moved_where_the_runner_will_not_collect_it_is_refused(self):
        """[L1] Under enforce, renaming a test file out of the collected pattern or folder is refused."""
        for target in ("tests/a_check.py", "archive/test_a.py"):
            with self.subTest(target):
                repo = Repo()
                (repo.dir / target).parent.mkdir(parents=True, exist_ok=True)
                repo.git("mv", "tests/test_a.py", target)
                repo.commit(f"move the test to {target}")
                self.refused(repo.push(), "test-moved")

    def test_a_rename_the_runner_still_collects_passes(self):
        """[L1] Under enforce, a test file renamed within the collected pattern is not a finding."""
        repo = Repo()
        repo.git("mv", "tests/test_a.py", "tests/test_b.py")
        repo.commit("rename within tests/")
        run = repo.push()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("[test-", run.stderr)

    def test_a_skip_passes_once_guard_allow_names_its_id(self):
        """[L1] A .guard-allow line naming the finding's id, committed at HEAD, lets that skip through."""
        repo = Repo()
        self.skip_test_one(repo)
        (finding,) = self.refused(repo.push(), "test-skipped", re.escape("tests/test_x.py"))
        repo.write(".guard-allow", f"{finding}  # owner: flaky on CI, tracked\n")
        repo.commit("the owner grants this skip")
        run = repo.push()
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_grant_on_disk_but_not_committed_does_not_pass(self):
        """[L1] .guard-allow is read from the pushed HEAD, so an uncommitted grant passes nothing."""
        repo = Repo()
        self.skip_test_one(repo)
        (finding,) = self.refused(repo.push(), "test-skipped")
        repo.write(".guard-allow", f"{finding}  # not committed\n")
        self.refused(repo.push(), "test-skipped")

    def test_a_grant_for_one_skip_does_not_pass_a_second_different_skip(self):
        """[L1] A grant covers only the id it names; a second, different skip is still refused."""
        repo = Repo()
        self.skip_test_one(repo)
        (granted,) = self.refused(repo.push(), "test-skipped")
        repo.write(".guard-allow", f"{granted}  # owner allowed test_one only\n")
        repo.commit("grant the first skip")
        repo.write("tests/test_x.py", repo.read("tests/test_x.py").replace(
            "    def test_two", '    @unittest.skip("y")\n    def test_two'))
        repo.commit("switch test_two off too")
        ids = self.refused(repo.push(), "test-skipped")
        self.assertTrue([i for i in ids if i != granted], f"only the granted id was reported: {ids}")

    def test_a_guard_allow_comment_on_the_line_alone_is_still_refused(self):
        """[L1] A `guard:allow` comment on the skip line is not a grant."""
        repo = Repo()
        self.skip_test_one(repo, marker='@unittest.skip("x")  # guard:allow')
        self.refused(repo.push(), "test-skipped")

    def test_observe_mode_prints_the_finding_and_does_not_refuse(self):
        """[L1] The law binds only with the gate on enforce: observe prints the finding and exits 0."""
        repo = Repo(guard="observe")
        self.skip_test_one(repo)
        run = repo.push()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(findings(run.stderr, "test-skipped"), run.stderr)

    def test_a_harmless_change_to_a_test_passes(self):
        """[L1] Adding an assertion to a test is not a finding."""
        repo = Repo()
        repo.write("tests/test_x.py", repo.read("tests/test_x.py").replace(
            "        self.assertEqual(1 + 1, 2)\n", "        self.assertEqual(1 + 1, 2)\n        self.assertEqual(3 - 1, 2)\n"))
        repo.commit("a stronger test")
        run = repo.push()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("[test-", run.stderr)

    # --- L2 ---
    def add_then_remove_a_token(self, repo):
        repo.write("config.py", f'TOKEN = "{TOKEN}"\n')
        repo.commit("add a token")
        repo.git("rm", "-q", "config.py")
        repo.commit("remove the token")
        self.assertNotIn(TOKEN, repo.git("grep", "-I", "-e", "", "HEAD", "--", ".").stdout)

    def test_a_token_added_then_removed_in_a_later_commit_is_refused(self):
        """[L2] A credential in any pushed commit is refused even though HEAD no longer has it."""
        repo = Repo()
        self.add_then_remove_a_token(repo)
        self.refused(repo.push(), "secret-history", re.escape("config.py"))

    def test_a_token_in_history_is_refused_with_the_guard_off_or_observing(self):
        """[L2] The secret-history refusal holds in every guard mode."""
        for mode in ("off", "observe"):
            with self.subTest(mode):
                repo = Repo(guard=mode)
                self.add_then_remove_a_token(repo)
                self.refused(repo.push(), "secret-history")

    def test_a_guard_allow_line_naming_a_secret_finding_does_not_pass_it(self):
        """[L2] No grant passes a credential in history."""
        repo = Repo()
        self.add_then_remove_a_token(repo)
        (finding,) = self.refused(repo.push(), "secret-history")
        repo.write(".guard-allow", f"{finding}  # test token, revoked\n")
        repo.commit("try to grant the token")
        self.assertIn(finding, self.refused(repo.push(), "secret-history"))


if __name__ == "__main__":
    unittest.main()
