# Evidence: PASS

- Commit: `4b0b891b9c` (change starts at `a221d26f72`, 2 files)
- Surfaces: logic. Intent: feature. Severity: high (labelled by rules).
- Recorded by: the author. Every result below was captured from a real run, not typed.

**Asked for:** Add 20% VAT at checkout.

## 1. a $40 cart costs $48 with 20% VAT — PASS

Surface: logic · environment: local

| | |
|---|---|
| Expected | status 200; output has `"to_pay": 48` |
| After (this commit) | meets it (exit 0, status 200, 0.02s) |

Ran:

```
curl -s -i "$EVIDENCE_URL/checkout?prices=20,20"
```

Got:

```
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.14.5
Date: Sun, 22 Nov 2026 09:51:46 GMT
Content-Type: application/json

{"to_pay": 48.0}
```

## 2. a price that is not a number is refused — PASS

Surface: logic · environment: local

| | |
|---|---|
| Expected | status 400; output has `must be numbers` |
| After (this commit) | meets it (exit 0, status 400, 0.03s) |

Ran:

```
curl -s -i "$EVIDENCE_URL/checkout?prices=20,abc"
```

Got:

```
HTTP/1.0 400 Bad Request
Server: BaseHTTP/0.6 Python/3.14.5
Date: Sun, 22 Nov 2026 09:51:47 GMT
Content-Type: application/json

{"error": "prices must be numbers"}
```
