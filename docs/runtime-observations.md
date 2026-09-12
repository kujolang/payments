# Runtime observation: chained dictionary assignment

Kujo 1.4.0, source checkout d054d87a9919544d4ac8eeb4b2ecc86500e71cb8, observed 2026-09-12.

`kujo run tests/runtime/nested_assignment_context_repro.kujo` exits zero and prints `minor:5500` after assigning `changed["charge"]["minor"] = 5501`. The interpreter rejects the same file with `Complex index assignment not yet supported`. The smaller `nested_assignment_repro.kujo` produces VM `Stack underflow` and the same interpreter rejection. This is context-dependent VM behavior, not a claim that the language supports nested assignment.

Payments uses explicit replacement of the nested dictionary. Its malicious-input tests assert the resulting behavior; they do not depend on chained mutation. Diagnostic reproducers are excluded from the normal passing test runner. The upstream runtime issue is unresolved; no Kujo source was modified by this implementation milestone.
