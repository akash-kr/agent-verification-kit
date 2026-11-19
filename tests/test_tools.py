"""Self-test for review-eval and diff-check. Run: python3 tests/test_tools.py (no network; a stub reviewer)."""
import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
# Flags "charge" in any added line as important, and everything else as a nit.
STUB = """\
import sys
for line in sys.stdin:
    if line.startswith("+") and "charge" in line:
        print("FINDING important: charges the card twice in " + line[1:].strip())
    elif line.startswith("+") and not line.startswith("+++"):
        print("FINDING nit: style")
"""


def sh(cwd, *cmd):
    run = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if run.returncode != 0:
        raise AssertionError(f"{cmd}: {run.stdout}{run.stderr}")
    return run.stdout


class Tools(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp())
        sh(self.repo, "git", "init", "-q", "-b", "main")
        (self.repo / "stub.py").write_text(STUB)
        self.commit("start", "def pay(card):\n    return card\n")
        self.bad =self.commit("pay(card)", "def pay(card):\n    charge(card)\n    charge(card)\n    return card\n")
        self.clean = self.commit("fix", "def pay(card):\n    charge(card)\n    return card\n")
        self.receipt = self.commit("receipt", "def pay(card):\n    charge(card)\n    charge_receipt(card)\n    return card\n")

    def commit(self, msg, app):
        (self.repo / "app.py").write_text(app)
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)
        return sh(self.repo, "git", "rev-parse", "HEAD").strip()

    def case(self, name, text):
        (self.repo / "evals/review").mkdir(parents=True, exist_ok=True)
        (self.repo / "evals/review" / f"{name}.toml").write_text(text)

    def eval(self, *args):
        return subprocess.run(["python3", str(SCRIPTS / "review-eval"), "--reviewer", "python3 stub.py", *args],
                              cwd=self.repo, capture_output=True, text=True)

    def test_review_eval_counts_caught_bugs_and_false_flags_per_set(self):
        self.case("double", f'id = "double-charge"\nkind = "bug"\ncommit = "{self.bad}"\nset = "test"\n'
                  'answer = "pay charges the card twice."\nmatch = ["charges", "twice"]\nsource = "test"\n')
        self.case("missed", f'id = "missed"\nkind = "bug"\ncommit = "{self.bad}"\nset = "test"\n'
                  'answer = "a bug the stub cannot see."\nmatch = ["refund"]\n')
        self.case("control", f'id = "clean-fix"\nkind = "control"\ncommit = "{self.clean}"\nset = "test"\n')
        self.case("receipt", f'id = "receipt"\nkind = "control"\ncommit = "{self.receipt}"\nset = "tune"\n')
        out = self.repo / "out.json"
        run = self.eval("--json", str(out))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("test: recall 1/2 bugs caught, false flags 0/1 clean changes", run.stdout)
        self.assertIn("tune: recall 0/0 bugs caught, false flags 1/1 clean changes", run.stdout)
        self.assertIn("answer: a bug the stub cannot see.", run.stdout)
        self.assertEqual({r["id"]: r["ok"] for r in json.loads(out.read_text())},
                         {"double-charge": True, "missed": False, "clean-fix": True, "receipt": False})
        self.assertNotIn("receipt", self.eval("--set", "test").stdout)

    def test_review_eval_grades_a_reviewer_that_exits_non_zero_and_runs_one_the_old_commit_lacks(self):
        (self.repo / "evals/review").mkdir(parents=True)
        self.case("double", f'id = "double-charge"\nkind = "bug"\ncommit = "{self.bad}"\nset = "test"\n'
                  'answer = "pay charges the card twice."\nmatch = ["charges", "twice"]\n')
        self.case("timeout", f'id = "clean"\nkind = "control"\ncommit = "{self.clean}"\nset = "test"\n')
        (self.repo / "review.sh").write_text("#!/bin/sh\npython3 \"$(dirname \"$0\")/stub.py\"\n[ \"$REVIEW_HEAD\" = \"%s\" ] && sleep 60\nexit 1\n" % self.clean)
        (self.repo / "review.sh").chmod(0o755)
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "a reviewer newer than the cases")
        run = subprocess.run(["python3", str(SCRIPTS / "review-eval"), "--reviewer", "./review.sh", "--timeout", "8"],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("test: recall 1/1 bugs caught, false flags 0/0 clean changes, errors 1", run.stdout)

    def test_review_eval_counts_a_reviewer_that_crashes_without_findings_as_an_error(self):
        self.case("clean", f'id = "clean"\nkind = "control"\ncommit = "{self.clean}"\nset = "test"\n')
        run = subprocess.run(["python3", str(SCRIPTS / "review-eval"), "--reviewer", "python3 -c 'raise SystemExit(1)'"],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertIn("test: recall 0/0 bugs caught, false flags 0/0 clean changes, errors 1", run.stdout)

    def test_diff_check_accepts_an_approved_input_that_both_sides_reject(self):
        (self.repo / "inputs").mkdir()
        (self.repo / "inputs/good.txt").write_text("1\n")
        (self.repo / "inputs/bad.txt").write_text("x\n")
        (self.repo / "num.py").write_text("import sys\nprint(int(sys.stdin.read()))\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "num")
        base = sh(self.repo, "git", "rev-parse", "HEAD").strip()
        args = ["python3", str(SCRIPTS / "diff-check"), "--cmd", "python3 num.py", "--base", base, "--inputs", "inputs"]
        self.assertEqual(subprocess.run(args, cwd=self.repo, capture_output=True).returncode, 1)
        (self.repo / "approved.txt").write_text("bad.txt  # both versions reject it\n")
        self.assertEqual(subprocess.run(args + ["--approved", "approved.txt"], cwd=self.repo, capture_output=True).returncode, 0)

    def test_review_eval_keeps_shell_syntax_and_reviews_a_merge_against_its_first_parent(self):
        sh(self.repo, "git", "checkout", "-q", "-b", "side", self.clean + "^")
        (self.repo / "other.py").write_text("x = 1\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "side")
        sh(self.repo, "git", "checkout", "-q", "main")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "merge", "-q", "--no-ff", "-m", "merge side", "side")
        merge = sh(self.repo, "git", "rev-parse", "HEAD").strip()
        self.case("merge", f'id = "merge"\nkind = "bug"\ncommit = "{merge}"\nset = "test"\nanswer = "adds other."\nmatch = ["other"]\n')
        (self.repo / "flag.py").write_text("import sys\nfor l in sys.stdin:\n    if l.startswith('+++') and 'other' in l: print('FINDING important: other added')\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "reviewer")
        run = subprocess.run(["python3", str(SCRIPTS / "review-eval"), "--reviewer", 'true ; python3 "$REVIEW_REPO/flag.py"'],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertIn("test: recall 1/1 bugs caught", run.stdout, run.stdout + run.stderr)

    def test_diff_check_fails_when_every_input_gives_no_output_on_both_sides(self):
        (self.repo / "inputs").mkdir()
        (self.repo / "inputs/a.txt").write_text("1\n")
        run = subprocess.run(["python3", str(SCRIPTS / "diff-check"), "--old", "no-such-cmd 2>/dev/null | cat", "--new", "no-such-cmd 2>/dev/null | cat", "--inputs", "inputs"],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stdout)

    def test_diff_check_fails_when_the_command_fails_on_both_sides(self):
        (self.repo / "inputs").mkdir()
        (self.repo / "inputs/a.txt").write_text("1\n")
        base = sh(self.repo, "git", "rev-parse", "HEAD").strip()
        run = subprocess.run(["python3", str(SCRIPTS / "diff-check"), "--cmd", "python3 no-such-file.py", "--base", base, "--inputs", "inputs"],
                             cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("fails on both", run.stdout)

    def test_review_eval_refuses_a_case_without_an_answer_key(self):
        self.case("bad", f'id = "x"\nkind = "bug"\ncommit = "{self.bad}"\nset = "test"\n')
        run = self.eval()
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("missing ['answer', 'match']", run.stderr)

    def test_diff_check_compares_error_output_when_asked(self):
        (self.repo / "inputs").mkdir()
        (self.repo / "inputs/a.txt").write_text("1\n")
        (self.repo / "say.py").write_text("import sys\nprint(sys.stdin.read())\nprint('warning: old', file=sys.stderr)\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "say")
        base = sh(self.repo, "git", "rev-parse", "HEAD").strip()
        (self.repo / "say.py").write_text("import sys\nprint(sys.stdin.read())\nprint('warning: new', file=sys.stderr)\n")
        args = ["python3", str(SCRIPTS / "diff-check"), "--cmd", "python3 say.py", "--base", base, "--inputs", "inputs"]
        self.assertEqual(subprocess.run(args, cwd=self.repo, capture_output=True).returncode, 0)
        self.assertEqual(subprocess.run(args + ["--stderr"], cwd=self.repo, capture_output=True).returncode, 1)

    def test_diff_check_flags_a_changed_output_unless_approved(self):
        (self.repo / "inputs").mkdir()
        (self.repo / "inputs/a.txt").write_text("1 2\n")
        (self.repo / "inputs/b.txt").write_text("3\n")
        (self.repo / "sum.py").write_text("import sys\nprint(sum(int(x) for x in sys.stdin.read().split()))\n")
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", "sum")
        base = sh(self.repo, "git", "rev-parse", "HEAD").strip()
        args = ["python3", str(SCRIPTS / "diff-check"), "--cmd", "python3 sum.py", "--base", base, "--inputs", "inputs"]
        self.assertEqual(subprocess.run(args, cwd=self.repo, capture_output=True).returncode, 0)
        (self.repo / "sum.py").write_text("import sys\nxs = sys.stdin.read().split()\nprint(sum(int(x) for x in xs) + (len(xs) > 1))\n")
        run = subprocess.run(args, cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(run.returncode, 1)
        self.assertIn("a.txt", run.stdout)
        self.assertNotIn("- b.txt", run.stdout)
        (self.repo / "approved.txt").write_text("a.txt  # intended: pairs get a bonus\n")
        self.assertEqual(subprocess.run(args + ["--approved", "approved.txt"], cwd=self.repo, capture_output=True).returncode, 0)


class Public(unittest.TestCase):
    def test_no_file_in_the_kit_names_a_home_folder_or_a_real_email_address(self):
        kit = SCRIPTS.parent
        local = re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+|/private/tmp|[A-Za-z]:\\\\Users")
        email = re.compile(r"[A-Za-z0-9._%+-]+@(?!example\.com\b|t\b)[A-Za-z0-9-]+\.[A-Za-z]{2,}")
        for f in kit.rglob("*"):
            if f.is_file() and ".git" not in f.relative_to(kit).parts[:1] and "__pycache__" not in f.parts and f != Path(__file__).resolve():
                text = f.read_text(errors="ignore")
                self.assertIsNone(local.search(text), f"{f.name}: {local.search(text)}")
                self.assertIsNone(email.search(text), f"{f.name}: {email.search(text)}")


if __name__ == "__main__":
    unittest.main()
