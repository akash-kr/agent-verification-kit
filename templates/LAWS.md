# Laws

What must stay true in this repo. Only the owner adds or changes a line (`scripts/agent-check law|bug "<text>"`);
agents propose wording. A test names the line it holds, as `[L1]` or `[B1]`; a push refuses a new test that
names none, and a bug test that already passes on the code before the fix. Each line says what holds it,
cheapest first: architecture (one door, one owner of the write), a type, a lint, then a test.

<!-- Example (delete it): L1: A paid API call is made only after the request's budget check passes. — held by: architecture (billing.charge is the one door) and test tests/test_billing.py::test_no_charge_without_budget -->

## Bugs
