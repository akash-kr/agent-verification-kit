"""The shop's test runner, so the examples need nothing but Python.
  python3 run_tests.py               every test_ function in tests/
  python3 run_tests.py FILE NAME     one test. Exit 0 pass, 1 fail, 2 cannot run (as pytest does)."""
import importlib.util
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def load(file):
    spec = importlib.util.spec_from_file_location(Path(file).stem, file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


try:
    if len(sys.argv) == 3:
        targets = [(sys.argv[1], getattr(load(sys.argv[1]), sys.argv[2]))]
    else:
        targets = [(str(f), fn) for f in sorted(Path("tests").glob("test_*.py"))
                   for name, fn in vars(load(f)).items() if name.startswith("test_") and callable(fn)]
except Exception as error:  # a file that will not load, or a test that is not there
    print(f"cannot run: {error!r}", file=sys.stderr)
    sys.exit(2)
failed = 0
for file, fn in targets:
    try:
        fn()
    except AssertionError as error:
        failed += 1
        print(f"FAIL {file}::{fn.__name__}: {str(error) or traceback.extract_tb(error.__traceback__)[-1].line}")
print(f"{len(targets) - failed} passed, {failed} failed")
sys.exit(1 if failed else 0)
