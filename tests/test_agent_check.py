"""The setup's own check: agent-check must refuse each bad push or commit and allow its good twin.

Run: python3 tests/test_agent_check.py   (no network, no dependencies; builds throwaway repos)
"""
import hashlib
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent / "scripts" / "agent-check"
RUNNER = """\
import importlib.util, sys
# Exits as pytest does: 1 when a test fails, 2 when its file cannot be loaded, 4 when no such test exists.
def run(file, name=None):
    spec = importlib.util.spec_from_file_location("t", file); m = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(m)
    except Exception:
        sys.exit(2)
    classes = [c for c in dir(m) if c.startswith("Test")]
    for n in [name] if name else [n for n in dir(m) if n.startswith("test_")] + [f"{c}::{n}" for c in classes for n in dir(getattr(m, c)) if n.startswith("test_")]:
        *cls, fn = n.split("::")
        holder = getattr(m, cls[0], None) if cls else m
        if not hasattr(holder, fn):
            sys.exit(4)
        getattr(holder() if cls else holder, fn)()
if len(sys.argv) > 1:
    run(*sys.argv[1:])
else:
    import glob
    for f in glob.glob("tests/test_*.py"):
        run(f)
"""
CONFIG = 'test = "python3 run.py"\none_test = "python3 run.py {file} {name}"\ntests = "tests/"\n'


def sh(cwd, *cmd, ok=True):
    run = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if ok and run.returncode != 0:
        raise AssertionError(f"{cmd} failed: {run.stdout}{run.stderr}")
    return run


class Practice(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        origin, self.repo = self.tmp / "origin.git", self.tmp / "work"
        sh(self.tmp, "git", "init", "-q", "--bare", "-b", "main", str(origin))
        sh(self.tmp, "git", "clone", "-q", str(origin), str(self.repo))
        self.write("run.py", RUNNER)
        self.write(".gitignore", "__pycache__/\n.test-tmp/\n")
        self.write("agent-check.toml", CONFIG)
        self.write("app.py", "def total(xs):\n    return sum(xs)\n")
        self.write("LAWS.md", "# Laws\n\nL1: total adds every item.\n")
        self.write("tests/test_app.py", "from app import total\n\ndef test_total():\n    \"\"\"[L1]\"\"\"\n    assert total([1, 2]) == 3\n")
        self.commit("start")
        sh(self.repo, "git", "push", "-q", "-u", "origin", "main")

    def write(self, path, text):
        (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / path).write_text(text)

    def commit(self, msg):
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)

    def check(self, *args, stdin=""):
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        return subprocess.run(["python3", str(TOOL), *args], cwd=self.repo, capture_output=True, text=True, env=env, input=stdin)

    def add_test(self, body, app=None):
        if app:
            self.write("app.py", app)
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text() + textwrap.dedent(body))
        self.commit("change")

    # --- push ---
    def test_a_bug_test_that_fails_on_the_old_code_passes(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0, not an error.\n")
        self.add_test('\ndef test_empty():\n    """[B1]"""\n    assert total(None) == 0\n', app="def total(xs):\n    return sum(xs or [])\n")
        self.check("seal", "tests/test_app.py::test_empty")
        self.commit("seal the bug test")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_test_naming_no_law_is_refused(self):
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("names no law", run.stderr)

    def test_a_test_naming_an_unknown_id_is_refused(self):
        self.add_test('\ndef test_two():\n    """[L9]"""\n    assert total([2]) == 2\n')
        self.assertIn("names no law", self.check("push").stderr)

    def test_a_new_test_that_already_passes_on_the_old_code_is_refused(self):
        self.add_test('\ndef test_two():\n    """[L1]"""\n    assert total([2, 2]) == 4\n')
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("passes on the old code", run.stderr)

    def test_a_test_for_a_law_added_in_this_push_may_already_pass(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: total never changes its input.\n")
        self.add_test('\ndef test_input_kept():\n    """[L2]"""\n    xs = [1]\n    total(xs)\n    assert xs == [1]\n')
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("added in this push, and is not sealed", run.stderr)
        self.check("seal", "tests/test_app.py::test_input_kept")
        self.commit("seal the law test")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_bug_test_that_only_fails_to_load_on_the_old_code_is_refused(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.write("app.py", "def total(xs):\n    return sum(xs)\n\ndef helper():\n    return None\n")
        self.write("tests/test_empty.py", 'from app import total, helper\n\ndef test_empty():\n    """[B1]"""\n    assert total([]) == 0\n')
        self.commit("a bug test already true on the old code, behind a new import")
        self.check("seal", "tests/test_empty.py::test_empty")
        self.commit("seal")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_empty could not run on the old code", run.stderr)

    def test_a_test_in_a_class_runs_by_its_class_on_the_old_code(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.add_test('\nclass TestEmpty:\n    def test_empty(self):\n        """[B1]"""\n        assert total([]) == 0\n')
        self.check("seal", "tests/test_app.py::TestEmpty::test_empty")
        self.commit("seal")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("TestEmpty::test_empty passes on the old code", run.stderr)

    def test_a_class_test_sharing_an_old_tests_name_is_still_a_new_test(self):
        self.add_test("\nclass TestTwo:\n    def test_total(self):\n        assert total([2, 2]) == 4\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("TestTwo::test_total names no law", run.stderr)

    def test_a_push_with_uncommitted_changes_is_refused_as_the_suite_would_not_run_the_commit(self):
        self.write("app.py", "def total(xs):\n    return 0\n")
        self.commit("break")
        self.write("app.py", "def total(xs):\n    return sum(xs)\n")  # the fix, left uncommitted
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("uncommitted", run.stderr)
        sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        self.write("helper.py", "X = 1\n")  # an untracked file the suite could import
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("helper.py", run.stderr)

    def test_a_runner_that_cannot_run_the_old_code_refuses_rather_than_passing_every_new_test(self):
        self.write("agent-check.toml", CONFIG.replace('one_test = "python3 run.py', 'one_test = "python3 missing.py'))
        self.commit("break the runner")
        sh(self.repo, "git", "push", "-q")
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.add_test('\ndef test_empty():\n    """[B1]"""\n    assert total(None) == 0\n', app="def total(xs):\n    return sum(xs or [])\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("could not run the old code", run.stderr)

    def test_ci_checks_the_commits_after_a_given_base_without_fetching_or_rerunning_the_suite(self):
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        self.write("app.py", "def total(xs):\n    return 0\n")  # the suite would fail, and --no-suite skips it
        self.add_test('\ndef test_two():\n    """[L1]"""\n    assert total([2, 2]) == 0\n')
        sh(self.repo, "git", "remote", "remove", "origin")  # CI never fetches
        run = self.check("push", "--base", start, "--no-suite")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text() + "\ndef test_three():\n    assert True\n")
        self.commit("untagged")
        run = self.check("push", "--base", start, "--no-suite")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_three names no law", run.stderr)

    def test_a_push_needs_real_app_proof_newer_than_the_last_commit_but_ci_does_not(self):
        self.write("agent-check.toml", CONFIG + 'fresh = [".test-tmp/check-*/passed"]\n')
        self.commit("ask for proof")
        start = sh(self.repo, "git", "rev-parse", "HEAD~1").stdout.strip()
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("no .test-tmp/check-*/passed from a passing run on this commit", run.stderr)
        head = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        proof = self.repo / ".test-tmp/check-8798/passed"
        proof.parent.mkdir(parents=True)
        proof.write_text(f"{start}\nclean\n")  # a run on an earlier commit does not count, however new the file
        self.assertEqual(self.check("push").returncode, 1)
        proof.write_text(f"{head}\ndirty\n")  # nor a run with uncommitted changes
        self.assertEqual(self.check("push").returncode, 1)
        proof.write_text(f"{head}\nclean\n")  # nor a proof with no screenshot hashes
        self.assertEqual(self.check("push").returncode, 1)
        shot = proof.parent / "feed.png"
        shot.write_bytes(b"real screenshot")
        digest = hashlib.sha256(b"real screenshot").hexdigest()
        proof.write_text(f"{head}\nclean\n{digest}  {shot}\n")
        self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)
        shot.write_bytes(b"swapped later")  # a screenshot changed after the run does not count
        self.assertEqual(self.check("push").returncode, 1)
        proof.unlink()
        self.assertEqual(self.check("push", "--base", start, "--no-suite").returncode, 0)
        self.assertEqual(self.check("push", "--base", start).returncode, 0)  # CI running the suite still has no proof to show

    def test_docs_only_pushes_and_branch_deletes_need_no_proof_and_another_commit_is_refused(self):
        self.write("agent-check.toml", CONFIG + 'fresh = [".test-tmp/check-*/passed"]\n')
        self.commit("ask for proof")
        sh(self.repo, "git", "push", "-q")
        self.write("README.md", "notes\n")
        self.commit("docs only")
        self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)
        zero = "0" * 40
        self.assertEqual(self.check("push", "--hook", stdin=f"(delete) {zero} refs/heads/old {'a' * 40}\n").returncode, 0)
        other = f"refs/heads/x {'b' * 40} refs/heads/main {zero}\n"
        run = self.check("push", "--hook", stdin=other)
        tag = f"refs/tags/v1 {'c' * 40} refs/tags/v1 {zero}\n"
        self.assertEqual(self.check("push", "--hook", stdin=tag).returncode, 0)
        self.assertEqual(run.returncode, 1)
        self.assertIn("only on the checked-out commit", run.stderr)

    def test_a_commit_staging_a_high_stakes_path_suggests_a_review_before_the_push(self):
        self.write("agent-check.toml", CONFIG + 'review = ["app.py"]\n')
        self.commit("watch app.py")
        self.write("app.py", "def total(xs):\n    return sum(xs)  # touched\n")
        sh(self.repo, "git", "add", "app.py")
        run = self.check("commit")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("fresh review suggested before you push", run.stderr)
        self.assertIn("app.py", run.stderr)

    def test_a_failing_suite_is_refused(self):
        self.write("app.py", "def total(xs):\n    return 0\n")
        self.commit("break")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("full suite failed", run.stderr)

    def test_a_push_behind_upstream_is_refused(self):
        other = self.tmp / "other"
        sh(self.tmp, "git", "clone", "-q", str(self.tmp / "origin.git"), str(other))
        (other / "x.txt").write_text("x")
        sh(other, "git", "add", "x.txt")
        sh(other, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "other")
        sh(other, "git", "push", "-q")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("behind", run.stderr)

    def test_a_sealed_test_that_changes_is_refused_and_a_reseal_is_shown(self):
        self.assertEqual(self.check("seal", "tests/test_app.py::test_total").returncode, 0)
        self.assertIn("tests/test_app.py::test_total", (self.repo / ".sealed-tests").read_text())
        self.commit("seal the law test")
        sh(self.repo, "git", "push", "-q")
        self.write("app.py", "def total(xs):\n    return sum(xs)  # implementer works\n")
        self.commit("code")
        self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)  # untouched seal passes
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("== 3", "> 0"))
        self.commit("weaken the sealed test")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_total is sealed and no longer matches", run.stderr)
        self.check("seal", "tests/test_app.py::test_total")  # an agent re-sealing its own edit is refused
        self.commit("reseal")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("but the law it holds did not change", run.stderr)
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text().replace("adds every item", "adds every item, and only positive totals count"))
        self.commit("the owner changes L1")  # with its law changed, the re-seal passes and is shown
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("re-sealed or unsealed with its law's change", run.stderr)
        self.assertEqual(self.check("seal", "tests/test_app.py::test_missing").returncode, 1)

    def test_a_reseal_after_the_commit_that_changed_its_law_is_refused(self):
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("seal the law test")
        sh(self.repo, "git", "push", "-q")
        for owner_changes_the_test in (True, False):
            self.write("LAWS.md", (self.repo / "LAWS.md").read_text().replace("adds every item", "adds every item, in any order"))
            if owner_changes_the_test:
                self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("total([1, 2])", "total([2, 1])"))
                self.check("seal", "tests/test_app.py::test_total")
            self.commit("the owner changes L1")
            self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)
            self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("== 3", "> 0"))
            self.check("seal", "tests/test_app.py::test_total")
            self.commit("weaken it and re-seal in a later commit of the same push")
            run = self.check("push")
            self.assertEqual(run.returncode, 1, f"owner changed the test: {owner_changes_the_test}")
            self.assertIn("sealed in this push and then changed and re-sealed", run.stderr)
            sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")

    def test_a_new_laws_test_is_sealed_as_first_written_and_may_change_with_a_later_change_to_its_law(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: total of one item is that item.\n")
        self.add_test('\ndef test_one():\n    """[L2]"""\n    assert total([5]) == 5\n')
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("total([5]) == 5", "total([5]) > 0"))
        self.check("seal", "tests/test_app.py::test_one")
        self.commit("weaken it, then seal it for the first time")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("sealed in this push and then changed and re-sealed", run.stderr)
        sh(self.repo, "git", "reset", "-q", "--hard", "HEAD~1")
        self.check("seal", "tests/test_app.py::test_one")
        self.commit("seal it as written")
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text().replace("is that item.", "is that item, for any item."))
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("total([5]) == 5", "total([7]) == 7"))
        self.check("seal", "tests/test_app.py::test_one")
        self.commit("the owner rewords L2 and re-seals its test")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_sealed_test_put_back_after_its_laws_change_is_refused(self):
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("seal the law test")
        sh(self.repo, "git", "push", "-q")
        original = (self.repo / "tests/test_app.py").read_text()
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text().replace("adds every item", "adds every item, and nothing is 0"))
        self.write("tests/test_app.py", original.replace("== 3\n", "== 3\n    assert total([]) == 0\n"))
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("the owner changes L1 and strengthens its test")
        self.write("tests/test_app.py", original)
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("put the old test and seal back")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("the test was then put back as it was", run.stderr)

    def test_an_unchanged_test_naming_a_law_added_now_must_be_sealed(self):
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace('"""[L1]"""', '"""[L1] [L2]"""'))
        self.commit("a test already naming a law to come")
        sh(self.repo, "git", "push", "-q")
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: total of two items adds them.\n")
        self.commit("add L2 only")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_total holds L2, added in this push, and is not sealed", run.stderr)

    def test_a_tagged_test_under_a_block_can_be_sealed_and_pushed(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0, not an error.\n")
        self.add_test('\nif True:\n    def test_empty():\n        """[B1]"""\n        assert total(None) == 0\n', app="def total(xs):\n    return sum(xs or [])\n")
        self.assertEqual(self.check("seal", "tests/test_app.py::test_empty").returncode, 0)
        self.commit("seal")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_sealed_test_re_tagged_with_a_new_law_may_be_re_sealed(self):
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("seal the law test")
        sh(self.repo, "git", "push", "-q")
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: total of two items adds them.\n")
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace('"""[L1]"""', '"""[L1] [L2]"""'))
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("the owner adds L2 and re-seals the test that holds it")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_test_defined_twice_is_refused_and_a_helper_class_is_not_a_test(self):
        self.add_test('\nif True:\n    def test_branch():\n        assert True\nelse:\n    def test_branch():\n        """[L1]"""\n        assert True\n')
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_branch is defined more than once", run.stderr)
        sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        self.add_test("\nclass Helper:\n    def test_connection(self):\n        return True\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_an_old_test_tagged_with_a_new_law_must_be_sealed(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: total of two items adds them.\n")
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace('"""[L1]"""', '"""[L1] [L2]"""'))
        self.commit("re-tag an old test")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_total holds L2, added in this push, and is not sealed", run.stderr)

    def test_a_test_in_any_class_or_block_is_found(self):
        self.add_test("\nimport unittest\n\nclass Regression(unittest.TestCase):\n    def test_x(self):\n        assert total([1]) == 1\n\nif True:\n    def test_y():\n        assert total([1]) == 1\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("Regression::test_x names no law", run.stderr)
        self.assertIn("test_y names no law", run.stderr)

    def test_the_old_code_runs_the_tests_as_committed_not_as_on_disk(self):
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.add_test('\ndef test_empty():\n    """[B1]"""\n    assert total([]) == 0\n')
        self.check("seal", "tests/test_app.py::test_empty")
        self.commit("seal a bug test that already holds on the old code")
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("total([]) == 0", "total(None) == 0"))
        run = self.check("push", "--base", start, "--no-suite")  # CI never checks the tree is clean
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_empty passes on the old code", run.stderr)

    def test_a_seal_cannot_be_deleted_or_dodged_and_reformatting_keeps_it(self):
        self.write("tests/test_app.py", "from app import total\n\ndef keep(f):\n    return f\n\n@keep\ndef test_total():\n    \"\"\"[L1]\"\"\"\n    note = '''\nleft margin text\n'''\n    assert total([1, 2]) == 3\n\nclass TestTwo:\n    def test_total(self):\n        \"\"\"[L1]\"\"\"\n        assert total([2]) == 2\n")
        self.check("seal", "tests/test_app.py::test_total", "tests/test_app.py::TestTwo::test_total")
        self.commit("seal")
        sh(self.repo, "git", "push", "-q")
        original = (self.repo / "tests/test_app.py").read_text()
        cases = {
            "the decorator": original.replace("@keep\n", ""),
            "a line after a left-margin string": original.replace("== 3", "> 0"),
            "the same name in a class": original.replace("== 2", "> 0"),
        }
        for what, text in cases.items():
            self.write("tests/test_app.py", text)
            self.commit(what)
            self.assertEqual(self.check("push").returncode, 1, f"changing {what} should be refused")
            sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        self.write("tests/test_app.py", original.replace("    assert total([1, 2]) == 3", "    # a comment\n\n    assert total([1, 2]) == 3   "))
        self.commit("reformat")
        self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)  # comments and spacing keep the seal
        sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        (self.repo / ".sealed-tests").unlink()
        self.commit("drop the seals")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("its seal changed or was removed", run.stderr)

    def test_seals_resist_a_reworded_law_an_untagged_test_string_data_a_redefinition_and_a_same_push_reseal(self):
        self.write("tests/test_app.py", "from app import total\n\ndef test_total():\n    \"\"\"[L1]\"\"\"\n    data = \"\"\"\n# heading\n\nrow\n\"\"\"\n    assert total([1, 2]) == 3 and data\n\ndef test_untagged():\n    assert True\n")
        self.assertEqual(self.check("seal", "tests/test_app.py::test_untagged").returncode, 1)  # only a law's test is sealed
        self.assertEqual(self.check("seal", "tests/test_app.py::test_total").returncode, 0)
        self.commit("seal")
        sh(self.repo, "git", "push", "-q")
        original = (self.repo / "tests/test_app.py").read_text()
        for what, text in {
            "a '#' line inside a string": original.replace("# heading", "# changed"),
            "a later redefinition": original + "\ndef test_total():\n    assert True\n",
        }.items():
            self.write("tests/test_app.py", text)
            self.commit(what)
            self.assertEqual(self.check("push").returncode, 1, f"{what} should be refused")
            sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        self.write("tests/test_app.py", original.replace("== 3", "> 0"))
        self.check("seal", "tests/test_app.py::test_total")
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text().replace("adds every item.", "adds every item"))
        self.commit("reseal behind a full stop")
        run = self.check("push")
        self.assertEqual(run.returncode, 1, "a changed full stop is not a changed law")
        sh(self.repo, "git", "reset", "-q", "--hard", "origin/main")
        self.write("tests/test_app.py", original + "\ndef test_more():\n    \"\"\"[L1]\"\"\"\n    assert total([3]) == 3\n")
        self.check("seal", "tests/test_app.py::test_more")
        self.commit("seal a new law test")
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("== 3\n", "> 0\n", 1).replace("total([3]) == 3", "total([3]) > 0"))
        self.check("seal", "tests/test_app.py::test_more")
        self.commit("weaken it and re-seal in the same push")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("sealed in this push and then changed and re-sealed", run.stderr)

    def test_a_rewritten_assertion_is_listed(self):
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("== 3", "> 0"))
        self.commit("weaken")
        run = self.check("push")
        self.assertIn("assertions removed or rewritten", run.stderr)
        self.assertIn("== 3", run.stderr)

    # --- commit ---
    def test_a_staged_credential_is_refused(self):
        self.write("config.py", 'API_KEY = "sk-' + "a" * 32 + '"\n')
        sh(self.repo, "git", "add", "config.py")
        run = self.check("commit")
        self.assertEqual(run.returncode, 1)
        self.assertIn("credential", run.stderr)

    def test_an_untracked_file_beside_a_staged_one_is_refused_and_allowed_once_added(self):
        self.write("app.py", "def total(xs):\n    return sum(xs)  # same\n")
        self.write("helper.py", "X = 1\n")
        sh(self.repo, "git", "add", "app.py")
        self.assertIn("helper.py: untracked", self.check("commit").stderr)
        sh(self.repo, "git", "add", "helper.py")
        self.assertEqual(self.check("commit").returncode, 0)

    def test_a_laws_change_is_shown(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "L2: new.\n")
        sh(self.repo, "git", "add", "LAWS.md")
        run = self.check("commit")
        self.assertEqual(run.returncode, 0)
        self.assertIn("Only the owner changes laws", run.stderr)

    def test_law_and_bug_take_the_next_id(self):
        self.check("law", "total is never negative for positive items.")
        self.check("bug", "a crash on None.")
        text = (self.repo / "LAWS.md").read_text()
        self.assertIn("L2: total is never negative", text)
        self.assertIn("B1: a crash on None.", text)

    # --- questions, gate modes, the Verified trailer, CI config from base, audit ---
    def test_a_commit_prints_only_the_questions_its_paths_trigger(self):
        self.write("agent-check.toml", CONFIG + '[[question]]\npaths = ["app.py"]\nask = "Does total still add every item?"\n'
                   '[[question]]\npaths = ["billing/"]\nask = "Can this charge twice?"\n')
        self.commit("questions")
        self.write("app.py", "def total(xs):\n    return sum(xs)  # touched\n")
        sh(self.repo, "git", "add", "app.py")
        run = self.check("commit")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Does total still add every item?", run.stderr)
        self.assertNotIn("Can this charge twice?", run.stderr)

    def test_a_gate_in_observe_mode_reports_and_logs_without_blocking_and_off_is_silent(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nlaws = "observe"\n')
        self.commit("observe laws")
        sh(self.repo, "git", "push", "-q")
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("would refuse", run.stderr)
        self.assertIn("test_two names no law", (self.repo / ".git/agent-check-observe.log").read_text())
        self.write("agent-check.toml", CONFIG + '[gates]\nlaws = "off"\n')
        self.commit("laws off")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertNotIn("test_two", run.stderr)

    def test_an_unknown_gate_or_mode_is_refused(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nlaws = "warn"\n')
        self.commit("bad mode")
        run = self.check("push")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("modes are off, observe, enforce", run.stderr)

    def test_the_verified_trailer_is_stamped_in_observe_and_required_with_a_reason_in_enforce(self):
        msg = self.repo / "MSG"
        msg.write_text("change\n")
        self.assertEqual(self.check("commit-msg", str(msg)).returncode, 0)  # off by default
        self.assertEqual(msg.read_text(), "change\n")
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "observe"\n')
        run = self.check("commit-msg", str(msg))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("Verified: none", msg.read_text())
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "enforce"\n')
        for text, ok in [("change\n", False), ("change\n\nVerified: none\n", False),
                         ("change\n\nVerified: none, docs only\n", True), ("change\n\nVerified: ran the suite, 35 passed\n", True)]:
            msg.write_text(text)
            self.assertEqual(self.check("commit-msg", str(msg)).returncode == 0, ok, text)

    def test_ci_reads_the_gates_from_the_base_so_a_change_cannot_loosen_its_own(self):
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        self.write("agent-check.toml", CONFIG + '[gates]\nlaws = "off"\n')
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        self.assertEqual(self.check("push", "--base", start, "--no-suite").returncode, 0)
        run = self.check("push", "--base", start, "--no-suite", "--config-from", start)
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_two names no law", run.stderr)
        self.assertEqual(self.check("push", "--base", start, "--config-from").returncode, 2)

    def test_audit_lists_what_is_stale_and_the_unverified_commits(self):
        self.write("LAWS.md", "# Laws\n\nL1: total adds every item.\nL2: nothing holds this.\n"
                   "L3: held by tests/test_gone.py::test_gone\n")
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "observe"\n')
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text() + '\ndef test_x():\n    """[L9]"""\n')
        self.write(".sealed-tests", "abc  tests/test_app.py::test_removed\n")
        self.commit("stale things")
        run = self.check("audit")
        self.assertEqual(run.returncode, 0, run.stderr)
        for expected in ["L2: no test names it", "tests/test_gone.py::test_gone, which no longer exists",
                         "names L9, which is not in LAWS.md", "test_removed seals a test that no longer exists",
                         "with no verification"]:
            self.assertIn(expected, run.stdout)
        self.assertNotIn("- L1:", run.stdout)

    # --- found in review ---
    def test_a_new_branch_with_no_upstream_or_origin_head_still_gets_every_check(self):
        sh(self.repo, "git", "config", "remote.origin.followRemoteHEAD", "never")
        sh(self.repo, "git", "remote", "set-head", "origin", "-d", ok=False)
        sh(self.repo, "git", "checkout", "-q", "-b", "feature")
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("test_two names no law", run.stderr)

    def test_a_first_push_to_an_empty_remote_runs_only_the_suite(self):
        empty = self.tmp / "empty.git"
        sh(self.tmp, "git", "init", "-q", "--bare", "-b", "main", str(empty))
        sh(self.repo, "git", "remote", "set-url", "origin", str(empty))
        sh(self.repo, "git", "branch", "--unset-upstream")
        sh(self.repo, "git", "update-ref", "-d", "refs/remotes/origin/main")
        sh(self.repo, "git", "remote", "set-head", "origin", "-d", ok=False)
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("first push", run.stderr)

    def test_config_from_a_commit_that_does_not_exist_is_refused(self):
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        run = self.check("push", "--base", start, "--no-suite", "--config-from", "0" * 40)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("cannot read agent-check.toml", run.stderr)

    def test_the_old_codes_own_test_runs_as_it_was_even_when_the_change_edits_it(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.write("app.py", "def total(xs):\n    return sum(xs or [])\n\ndef helper():\n    return None\n")
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text().replace("from app import total", "from app import total, helper").replace("== 3", "== 3 and helper() is None"))
        self.write("tests/test_empty.py", 'from app import total\n\ndef test_none():\n    """[B1]"""\n    assert total(None) == 0\n')
        self.commit("a fix that also edits the old test to use new code")
        self.check("seal", "tests/test_empty.py::test_none")
        self.commit("seal")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_renamed_test_file_does_not_make_its_tests_new(self):
        sh(self.repo, "git", "mv", "tests/test_app.py", "tests/test_total.py")
        self.write("tests/test_total.py", (self.repo / "tests/test_total.py").read_text() + "# moved\n")
        self.commit("rename the file and touch it")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_an_emptied_message_is_not_stamped_so_git_can_abort_the_commit(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "observe"\n')
        msg = self.repo / "MSG"
        msg.write_text("\n# Please enter the commit message\n")
        self.assertEqual(self.check("commit-msg", str(msg)).returncode, 0)
        self.assertNotIn("Verified", msg.read_text())

    def test_only_a_real_merge_skips_the_verified_gate(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "enforce"\n')
        msg = self.repo / "MSG"
        msg.write_text("Merge in a sneaky change\n")
        self.assertEqual(self.check("commit-msg", str(msg)).returncode, 1)
        (self.repo / ".git/MERGE_HEAD").write_text(sh(self.repo, "git", "rev-parse", "HEAD").stdout)
        self.assertEqual(self.check("commit-msg", str(msg)).returncode, 0)

    def test_ci_checks_the_verified_trailer_of_every_pushed_commit(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "enforce"\n')
        self.commit("enforce\n\nVerified: none, config only")
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        self.write("app.py", "def total(xs):\n    return sum(xs)  # skipped the hook\n")
        self.commit("no trailer, made with --no-verify")
        run = self.check("push", "--base", start, "--no-suite", "--config-from", start)
        self.assertEqual(run.returncode, 1)
        self.assertIn('no "Verified:" trailer', run.stderr)

    def test_a_question_without_an_ask_is_refused_by_name(self):
        self.write("agent-check.toml", CONFIG + '[[question]]\npaths = ["app.py"]\n')
        sh(self.repo, "git", "add", "agent-check.toml")
        run = self.check("commit")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("[[question]]", run.stderr)

    def test_an_untracked_file_beside_a_staged_one_is_found_in_a_folder_with_a_space(self):
        self.write("my dir/app.py", "X = 1\n")
        self.write("my dir/helper.py", "Y = 1\n")
        sh(self.repo, "git", "add", "my dir/app.py")
        self.assertIn("my dir/helper.py: untracked", self.check("commit").stderr)

    def test_audit_counts_untagged_tests_and_names_questions_that_match_no_file(self):
        self.write("agent-check.toml", CONFIG + '[[question]]\npaths = ["billing/"]\nask = "Twice?"\n')
        self.write("tests/test_app.py", (self.repo / "tests/test_app.py").read_text() + "\ndef test_a():\n    pass\n\ndef test_b():\n    pass\n")
        self.commit("legacy tests")
        run = self.check("audit")
        self.assertIn("2 tests name no law or bug", run.stdout)
        self.assertNotIn("test_a names", run.stdout)
        self.assertIn('question "Twice?" matches no tracked file', run.stdout)

    def test_a_git_revert_passes_the_verified_gate_at_commit_and_at_push(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "enforce"\n')
        self.commit("enforce\n\nVerified: none, config only")
        start = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        self.write("app.py", "def total(xs):\n    return sum(xs) + 0\n")
        self.commit("tweak\n\nVerified: ran the suite")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "revert", "--no-edit", "HEAD")
        msg = self.repo / "MSG"
        msg.write_text(sh(self.repo, "git", "log", "-1", "--format=%B").stdout)
        self.assertEqual(self.check("commit-msg", str(msg)).returncode, 0)
        run = self.check("push", "--base", start, "--no-suite", "--config-from", start)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_bug_test_in_a_folder_with_a_space_is_run_on_the_old_code(self):
        self.write("LAWS.md", (self.repo / "LAWS.md").read_text() + "B1: total of nothing is 0.\n")
        self.write("app.py", "def total(xs):\n    return sum(xs or [])\n")
        self.write("tests/edge cases/test_empty.py", 'import sys; sys.path.insert(0, ".")\nfrom app import total\n\ndef test_none():\n    """[B1]"""\n    assert total(None) == 0\n')
        self.commit("fix")
        self.check("seal", "tests/edge cases/test_empty.py::test_none")
        self.commit("seal")
        self.assertEqual(self.check("push").returncode, 0, self.check("push").stderr)
        self.write("tests/edge cases/test_empty.py", (self.repo / "tests/edge cases/test_empty.py").read_text() + "\ndef test_one():\n    \"\"\"[B1]\"\"\"\n    assert total([1]) == 1\n")
        self.commit("a bug test that passes on the old code")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("test_one passes on the old code", run.stderr)

    def test_git_settings_that_change_diff_output_do_not_hide_a_credential_or_a_new_test(self):
        for setting in ("color.ui=always", "diff.noprefix=true", "diff.mnemonicPrefix=true"):
            k, v = setting.split("=")
            sh(self.repo, "git", "config", k, v)
        self.write("conf.py", 'api_key = "abcdefghijklmnop1234567890"\n')
        sh(self.repo, "git", "add", "conf.py")
        self.assertEqual(self.check("commit").returncode, 1)
        sh(self.repo, "git", "rm", "-q", "--cached", "conf.py")
        (self.repo / "conf.py").unlink()
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        self.assertIn("test_two names no law", self.check("push").stderr)

    def test_a_push_from_a_subfolder_gets_every_check(self):
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        (self.repo / "sub").mkdir()
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        run = subprocess.run(["python3", str(TOOL), "push"], cwd=self.repo / "sub", capture_output=True, text=True, env=env)
        self.assertIn("test_two names no law", run.stderr)

    def test_a_new_branch_with_a_remote_not_named_origin_still_gets_every_check(self):
        sh(self.repo, "git", "remote", "rename", "origin", "up")
        sh(self.repo, "git", "checkout", "-q", "-b", "feature")
        self.add_test("\ndef test_two():\n    assert total([2]) == 2\n")
        run = self.check("push")
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertIn("test_two names no law", run.stderr)

    def test_a_new_branch_cut_before_main_moved_is_not_called_behind(self):
        sh(self.repo, "git", "config", "remote.origin.followRemoteHEAD", "never")
        sh(self.repo, "git", "remote", "set-head", "origin", "-d", ok=False)
        sh(self.repo, "git", "checkout", "-q", "-b", "feature")
        sh(self.repo, "git", "checkout", "-q", "main")
        self.write("app.py", "def total(xs):\n    return sum(xs)  # main moved\n")
        self.commit("main moves")
        sh(self.repo, "git", "push", "-q", "--no-verify", "origin", "main")
        sh(self.repo, "git", "checkout", "-q", "feature")
        self.write("notes.md", "x\n")
        self.commit("feature work")
        run = self.check("push")
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_a_revert_line_inside_a_message_does_not_exempt_it(self):
        self.write("agent-check.toml", CONFIG + '[gates]\nverified = "enforce"\n')
        msg = self.repo / "MSG"
        for body in ("real change\n\nThis reverts commit 1234567\n", "real change\n\nfixup! x\n"):
            msg.write_text(body)
            self.assertEqual(self.check("commit-msg", str(msg)).returncode, 1, body)

    def test_a_single_question_table_is_refused_by_name(self):
        for text in ('[question]\npaths = ["app.py"]\nask = "x?"\n', '[[question]]\npaths = [1]\nask = "x?"\n'):
            self.write("agent-check.toml", CONFIG + text)
            sh(self.repo, "git", "add", "agent-check.toml")
            run = self.check("commit")
            self.assertIn("[[question]]", run.stderr, text)
            self.assertNotIn("Traceback", run.stderr, text)

    def test_a_sealed_assertion_moved_into_a_block_that_never_runs_breaks_the_seal(self):
        self.write("tests/test_app.py", 'from app import total\n\ndef test_total():\n    """[L1]"""\n    if False:\n        pass\n    assert total([1, 2]) == 3\n')
        self.commit("a block")
        self.check("seal", "tests/test_app.py::test_total")
        self.commit("seal")
        sh(self.repo, "git", "push", "-q", "--no-verify", "origin", "main")
        self.write("tests/test_app.py", 'from app import total\n\ndef test_total():\n    """[L1]"""\n    if False:\n        pass\n        assert total([1, 2]) == 3\n')
        self.commit("the assertion can no longer run")
        run = self.check("push")
        self.assertEqual(run.returncode, 1)
        self.assertIn("no longer matches its seal", run.stderr)

    def test_a_law_goes_above_the_bugs_section_and_a_bug_below_it(self):
        self.write("LAWS.md", "# Laws\n\nL1: one.\n\n## Bugs\nB1: old bug.\n")
        self.check("law", "two.")
        self.check("bug", "new bug.")
        text = (self.repo / "LAWS.md").read_text()
        self.assertLess(text.index("L2: two."), text.index("## Bugs"))
        self.assertGreater(text.index("B2: new bug."), text.index("## Bugs"))


if __name__ == "__main__":
    unittest.main()
