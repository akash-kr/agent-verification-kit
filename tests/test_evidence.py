"""Self-test for scripts/evidence. Run: python3 tests/test_evidence.py (no network, no model: a stub classifier)."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CONFIG = ('test = "true"\none_test = "true"\ntests = "tests/"\nreview = ["billing/"]\n'
          '[gates]\nevidence = "enforce"\n[evidence]\nserve = "python3 -m http.server $PORT -d site"\nredact_env = ["APP_PIN"]\n')
TOTAL = "from pricing import total; import sys; print(total(int(sys.argv[1])))"


def sh(cwd, *cmd, ok=True):
    run = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if ok and run.returncode != 0:
        raise AssertionError(f"{cmd}: {run.stdout}{run.stderr}")
    return run


class Evidence(unittest.TestCase):
    def setUp(self):
        self.repo = Path(tempfile.mkdtemp()).resolve()
        sh(self.repo, "git", "init", "-q", "-b", "main")
        self.write("agent-check.toml", CONFIG)
        self.write(".gitignore", "evidence/\n__pycache__/\n")
        self.write("pricing.py", "def total(qty):\n    return qty * 10\n")
        self.write("site/index.html", "<h1>shop</h1>\n")
        self.commit("start")
        self.base = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()

    def write(self, path, text):
        (self.repo / path).parent.mkdir(parents=True, exist_ok=True)
        (self.repo / path).write_text(text)

    def commit(self, msg):
        sh(self.repo, "git", "add", "-A")
        sh(self.repo, "git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q", "-m", msg)

    def ev(self, *args, env=None):
        return subprocess.run(["python3", str(SCRIPTS / "evidence"), *args], cwd=self.repo, capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, env={**os.environ, **(env or {})})

    def labels(self):
        return json.loads(self.ev("classify", "--base", self.base).stdout.split("\nsurfaces:")[0])

    def fix(self):
        self.write("pricing.py", "def total(qty):\n    return max(qty, 0) * 10\n")
        self.commit("fix: a negative quantity totals 0")

    def page(self):
        return next((self.repo / "evidence").glob("*/evidence.md"))

    # --- classify ---
    def test_paths_set_the_severity_floor_even_for_a_file_moved_out_of_them(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.commit("rates")
        self.assertEqual(self.labels()["severity"], "high")
        self.base = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
        sh(self.repo, "git", "mv", "billing/rates.py", "rates.py")
        self.commit("move it out")
        self.assertEqual((self.labels()["severity"], self.labels()["level"]), ("high", "human"))

    def test_a_migration_is_at_least_medium_and_owes_its_own_evidence_beside_the_screen(self):
        self.write("migrations/002_add_price.sql", "ALTER TABLE t ADD price INT;\n")
        self.write("site/index.html", "<h1>shop 2</h1>\n")
        self.write("pricing.py", "def total(qty):\n    return qty * 11\n")
        self.commit("feat: prices")
        got = self.labels()
        self.assertEqual((got["severity"], got["owed"], got["intent"]), ("medium", ["migration", "ui"], "feature"))

    def test_a_classifier_can_add_a_surface_and_raise_severity_but_never_lower_it(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.commit("rates")
        self.write("agent-check.toml", CONFIG + 'classifier = "cat >/dev/null; echo \'{\\"surfaces\\": [\\"performance\\"], \\"intent\\": \\"refactor\\", \\"severity\\": \\"low\\"}\'"\n')
        got = self.labels()
        self.assertEqual((got["severity"], got["intent"]), ("high", "refactor"))
        self.assertIn("performance", got["owed"])
        self.write("pricing.py", "def total(qty):\n    return qty * 12\n")
        self.commit("small")
        self.base = sh(self.repo, "git", "rev-parse", "HEAD~1").stdout.strip()
        self.write("agent-check.toml", CONFIG + 'classifier = "echo \'{\\"severity\\": \\"high\\"}\'"\n')
        self.assertEqual(self.labels()["severity"], "high")

    # --- record ---
    def test_a_bug_case_shows_the_old_code_failing_and_a_case_that_already_passed_is_flagged(self):
        self.fix()
        self.assertEqual(self.ev("start", "--base", self.base).returncode, 0)
        run = self.ev("run", "--case", "a negative quantity totals 0", "--input", "qty=-2", "--before", "--expect-output", "0", "--", "python3", "-c", TOTAL, "-2")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(self.ev("finish").returncode, 0)
        text = self.page().read_text()
        self.assertIn("# Evidence: PASS", text)
        self.assertIn("| Input | qty=-2 |", text)
        self.assertIn("| Before (old code) | does not: output differs", text)
        self.assertIn("On the old code it gave:\n\n```\n-20", text)
        run = self.ev("run", "--case", "three items", "--before", "--expect-output", "30", "--", "python3", "-c", TOTAL, "3")
        self.assertEqual(run.returncode, 1)
        self.assertIn("passes on the old code", run.stdout)
        self.assertEqual(self.ev("finish").returncode, 1)
        self.assertIn("# Evidence: INCOMPLETE", self.page().read_text())

    def test_a_bug_fix_with_no_before_run_and_a_command_the_old_code_cannot_run_are_incomplete(self):
        self.fix()
        self.ev("start", "--base", self.base)
        self.ev("run", "--case", "after only", "--expect-output", "0", "--", "python3", "-c", TOTAL, "-2")
        self.assertIn("no case replayed on the old code", self.ev("finish").stdout)
        self.write("check.sh", "python3 -c '%s' -2\n" % TOTAL)
        self.commit("fix: add a script the old code lacks")
        self.ev("start", "--base", self.base)
        run = self.ev("run", "--case", "script", "--before", "--expect-output", "0", "--", "sh", "-c", "exec ./check.sh")
        self.assertIn("inconclusive", run.stdout + self.ev("finish").stdout)

    def test_secrets_are_replaced_in_the_command_and_the_output_and_the_app_is_started_for_the_run(self):
        self.fix()
        self.ev("start", "--base", self.base)
        line = 'curl -s -i -H "Authorization: Bearer sk-live-abcdef0123456789" "$EVIDENCE_URL/" && echo "pin=$APP_PIN mail=someone@example.com api_key=abcdef0123456789"'
        run = self.ev("run", "--case", "home page", "--expect-status", "200", "--expect-contains", "shop", "--", line, env={"APP_PIN": "4471993"})
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        raw = next((self.repo / "evidence").glob("*/cases.jsonl")).read_text()
        for secret in ("sk-live-abcdef0123456789", "4471993", "someone@example.com", "abcdef0123456789"):
            self.assertNotIn(secret, raw)
        self.assertIn("<h1>shop</h1>", raw)

    def test_a_write_on_production_is_refused_with_nobody_at_the_terminal_and_a_read_runs(self):
        self.write("agent-check.toml", CONFIG + '[evidence.env.live]\nhosts = ["api.shop.example"]\nproduction = true\n')
        self.fix()
        self.ev("start", "--base", self.base)
        run = self.ev("run", "--case", "hits live", "--", "echo", "https://api.shop.example/orders")
        self.assertIn("names a production host", run.stderr)
        run = self.ev("run", "--case", "write", "--env", "live", "--", "echo", "https://api.shop.example/orders")
        self.assertIn("nobody is at a terminal", run.stderr)
        run = self.ev("run", "--case", "read", "--env", "live", "--read-only", "--", "echo", "https://api.shop.example/orders")
        self.assertEqual(run.returncode, 0, run.stderr)

    # --- the gate ---
    def test_a_high_push_is_refused_without_passing_evidence_for_this_commit_and_an_edited_page_breaks_it(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.commit("feat: rates")
        check = lambda: self.ev("check", "--base", self.base)
        self.assertEqual(check().returncode, 1)
        self.assertIn("high severity", check().stderr)
        self.ev("start", "--base", self.base)
        self.assertEqual(check().returncode, 1)
        self.ev("run", "--case", "the rate", "--expect-output", "2", "--", "python3", "-c", "from billing.rates import RATE; print(RATE)")
        self.assertEqual(self.ev("finish").returncode, 0)
        self.assertEqual(check().returncode, 0, check().stderr)
        self.assertIn("read it before you push", check().stderr)
        self.assertIn("| PASS |", (self.repo / "evidence/INDEX.md").read_text())
        self.page().write_text(self.page().read_text().replace("PASS", "PASS!"))
        self.assertEqual(check().returncode, 1)
        self.ev("finish")
        self.write("billing/rates.py", "RATE = 3\n")
        self.commit("feat: rates again")
        self.assertEqual(check().returncode, 1)

    def test_a_labels_file_edited_to_low_does_not_pass_a_high_push(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.commit("feat: rates")
        self.ev("start", "--base", self.base)
        self.ev("run", "--case", "the rate", "--expect-output", "2", "--", "python3", "-c", "from billing.rates import RATE; print(RATE)")
        folder = self.page().parent if self.ev("finish").returncode == 0 else None
        labels = json.loads((folder / "labels.json").read_text())
        (folder / "labels.json").write_text(json.dumps({**labels, "severity": "low"}))
        self.ev("finish")  # even with a fresh proof over the edited labels
        self.assertEqual(self.ev("check", "--base", self.base).returncode, 1)

    def test_medium_and_low_owe_what_the_owner_set(self):
        def migrate(n):
            self.base = sh(self.repo, "git", "rev-parse", "HEAD").stdout.strip()
            self.write(f"migrations/{n}.sql", "ALTER TABLE t ADD price INT;\n")
            self.commit("feat: a column")
            return self.ev("check", "--base", self.base)
        self.assertEqual(migrate(2).returncode, 1)  # medium owes "agent" by default
        self.write("agent-check.toml", CONFIG + '[evidence.owes]\nmedium = "none"\n')
        self.commit("the owner's setting")
        self.assertEqual(migrate(3).returncode, 0)
        self.write("agent-check.toml", CONFIG + '[evidence.owes]\nhigh = "none"\n')
        self.commit("not allowed")
        self.assertIn("high is always", migrate(4).stderr)

    def test_a_push_that_edits_the_config_is_still_judged_by_the_config_before_it(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.write("agent-check.toml", CONFIG.replace('review = ["billing/"]', "review = []").replace('"enforce"', '"off"'))
        self.commit("feat: rates, and nothing is high any more")
        run = self.ev("check", "--base", self.base)
        self.assertEqual(run.returncode, 1)
        self.assertIn("high severity", run.stderr)

    def test_nothing_recorded_names_the_machines_folders(self):
        self.write("billing/rates.py", "RATE = 2\n")
        self.commit("feat: rates")
        self.ev("start", "--base", self.base)
        self.ev("run", "--case", "where am I", "--expect-contains", "rates", "--", "sh", "-c", 'echo "$PWD/billing/rates.py $HOME/notes"')
        self.assertEqual(self.ev("finish").returncode, 0)
        self.assertEqual(self.ev("check", "--base", self.base).returncode, 0)
        folder = self.page().parent
        for f in folder.iterdir():
            if f.is_file():
                self.assertNotIn(str(self.repo), f.read_text(), f.name)
                self.assertNotIn(os.path.expanduser("~"), f.read_text(), f.name)

    def test_old_recordings_are_pruned_and_the_text_and_high_severity_stay(self):
        shot = self.repo / "shot.png"
        for name, severity in (("2020-01-01-old-aaaaaaaaaa", "low"), ("2020-01-01-big-bbbbbbbbbb", "high")):
            self.write(f"evidence/{name}/labels.json", json.dumps({"head": self.base, "severity": severity, "surfaces": ["ui"], "intent": "feature", "verdict": "PASS"}))
            self.write(f"evidence/{name}/evidence.md", "# Evidence: PASS\n")
            self.write(f"evidence/{name}/media/a.png", "x")
        self.assertIn("pruned 1 media", self.ev("prune").stdout)
        self.assertTrue((self.repo / "evidence/2020-01-01-old-aaaaaaaaaa/evidence.md").exists())
        self.assertFalse((self.repo / "evidence/2020-01-01-old-aaaaaaaaaa/media").exists())
        self.assertTrue((self.repo / "evidence/2020-01-01-big-bbbbbbbbbb/media/a.png").exists())
        self.assertFalse(shot.exists())


if __name__ == "__main__":
    unittest.main()
