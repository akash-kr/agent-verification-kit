# Laws

Only the owner adds or changes these lines (`agent-check law|bug`). A test names the line it holds, as [L1] or [B1].
L1: With the guard gate on enforce, a push that adds a skip marker to a test, deletes a test file, or moves a test file where the runner won't collect it is refused, unless .guard-allow names that exact finding.
L2: A push is refused when any of its commits adds a credential in a known format, even if a later commit removes it.
