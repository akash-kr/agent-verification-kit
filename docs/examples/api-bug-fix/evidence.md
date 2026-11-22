# Evidence: PASS

- Commit: `ee2072baf8` (change starts at `c391df35d4`, 1 files)
- Surfaces: logic. Intent: bug. Severity: low (labelled by rules).
- Recorded by: the author. Every result below was captured from a real run, not typed.

**Asked for:** A 10% coupon on a $40 cart charges $30. It should be $36.

## 1. a 10% coupon on a $40 cart totals $36 — PASS

Surface: logic · environment: local

| | |
|---|---|
| Expected | status 200; output has `"total": 36` |
| Before (old code) | does not: output lacks '"total": 36' (exit 0, status 200, 0.02s) |
| After (this commit) | meets it (exit 0, status 200, 0.02s) |

Ran:

```
curl -s -i "$EVIDENCE_URL/total?prices=20,20&coupon=10"
```

Got:

```
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.14.5
Date: Sun, 22 Nov 2026 09:51:24 GMT
Content-Type: application/json

{"total": 36.0}
```

On the old code it gave:

```
HTTP/1.0 200 OK
Server: BaseHTTP/0.6 Python/3.14.5
Date: Sun, 22 Nov 2026 09:51:24 GMT
Content-Type: application/json

{"total": 30.0}
```

## 2. a coupon that is not a number is refused — PASS

Surface: logic · environment: local

| | |
|---|---|
| Expected | status 400; output has `must be numbers` |
| After (this commit) | meets it (exit 0, status 400, 0.02s) |

Ran:

```
curl -s -i "$EVIDENCE_URL/total?prices=20,20&coupon=ten"
```

Got:

```
HTTP/1.0 400 Bad Request
Server: BaseHTTP/0.6 Python/3.14.5
Date: Sun, 22 Nov 2026 09:51:25 GMT
Content-Type: application/json

{"error": "prices and coupon must be numbers"}
```
