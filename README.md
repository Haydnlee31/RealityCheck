# RealityCheck

**RealityCheck** is a developer workflow tool built on IBM Bob IDE that turns a
documented application contract into reproducible, reviewable repair evidence.

It was created as a hackathon prototype demonstrating how an AI coding assistant
can provide structured, auditable support for regression testing and bounded
repair — while keeping humans in the loop at every acceptance decision.

---

## The problem

Developers working with legacy or rapidly-changing codebases face a common gap:
requirements exist in documents, but there is no systematic way to ask
*"is the running application consistent with this contract clause, and can I
prove it?"*

A chat agent can read the code and offer an opinion, but an opinion is not
evidence. The fix might be correct, but without reproducible test execution and
protected inputs, there is no auditable record that:

- the requirement was interpreted correctly and a human agreed;
- the application demonstrably failed before the repair;
- the repair was minimal and bounded to application code only;
- the application demonstrably passes after repair, against the same inputs.

RealityCheck addresses that gap.

---

## How RealityCheck uses IBM Bob IDE

RealityCheck is implemented as a **Bob skill** (`SKILL.md`) that guides Bob
through a structured, multi-stage workflow:

### Parallel investigation (subagents)
Bob spawns two independent read-only subagent investigators simultaneously:

- **Investigator A** reads `docs/application-contract.md`, `docs/source-notes.md`,
  and `fixtures/` to identify requirement candidates and their sources.
- **Investigator B** reads `sample_app/` to identify implementation assumptions
  that may diverge from those requirements.

The parent Bob agent synthesises both findings into a structured mismatch claim,
separating model interpretation from deterministic observation.

### Human acceptance checkpoint (mandatory)
The workflow **stops** after presenting the proposed finding to the developer.
No file is written and no test runs until the developer replies `ACCEPT`.
The acceptance decision — including the reviewer identity and timestamp — is
recorded in the evidence JSON for every run.

### Bounded, agent-driven repair
After acceptance, Bob applies the smallest repair to `sample_app/` that
satisfies the accepted regression test, without touching protected inputs,
the test suite, or the contract documents.

### Deterministic verification
All execution results — pass/fail, exit codes, test counts, application snapshot
hashes, and protected-manifest verification — are produced by
`realitycheck.runner`, a pure-Python module with no LLM involvement.
Bob reads those records; it does not determine them.

---

## Deterministic verification vs model interpretation

Every RealityCheck evidence report explicitly distinguishes:

| Label | What it means |
|---|---|
| **Model interpretation** | Requirement text, implementation assumption, counterexample, proposed mismatch — authored by the model, reviewed by a human before acceptance. |
| **Deterministic observation** | Execution IDs, exit codes, pass/fail counts, SHA-256 snapshot digests, protected-manifest status — recorded by `realitycheck.runner`, no LLM involved. |

The verdict `verified_for_tested_scenarios` is emitted by
`realitycheck.runner.compute_verdict`, not by the model.
The model cannot claim a test passed.

---

## Repository layout

```
docs/
  application-contract.md   — authoritative requirement contract
  source-notes.md           — data provenance notes
fixtures/                   — synthetic development fixtures (manifest.json)
sample_app/                 — the repair target
tests/
  existing/                 — baseline happy-path tests (5 tests, unchanged)
  regression/               — accepted regression tests (one per finding)
  tooling/                  — runner and report unit tests
realitycheck/
  runner.py                 — deterministic execution engine
  report.py                 — evidence-to-Markdown renderer
  evidence.schema.json      — JSON schema for evidence records
runs/
  baseline-001/             — initial baseline execution (pre-RC-001)
  rc-001/                   — RC-001 evidence (AC-001 invoice identifier)
  rc-002/                   — RC-002 and RC-003 evidence (Scenario 2)
  rc-002-pre/               — baseline snapshots recorded before Scenario 2
```

---

## Completed runs

### baseline-001 — initial baseline

Executed against the unmodified application before any RealityCheck run.

- Execution ID: `exec-baseline-001`
- Phase: `baseline`
- Outcome: **passed** — 5 tests, 0 failures
- Application snapshot: `3e7416b5…`

### RC-001 — Invoice identifier preservation (Scenario 1)

**Finding:** AC-001 — `invoice_no` is an opaque string; the application must
not strip leading zeros or apply any numeric coercion.

**Defect reproduced:** `_normalize` applied `str(int(record["invoice_no"]))`,
silently converting `"053636"` to `"53636"` before storage.
A lookup for `"053636"` returned zero rows.

**Repair:** one-line change in [`sample_app/importer.py`](sample_app/importer.py) —
`str(int(…))` replaced with `str(…)`.

**Evidence:** [`runs/rc-001/evidence.json`](runs/rc-001/evidence.json)
| [`runs/rc-001/report-v2.md`](runs/rc-001/report-v2.md)

| Phase | Execution ID | Outcome | Tests |
|---|---|---|---|
| Reproduction | `df96ba74…` | **failed** (exit 1) | 1 failure |
| Verification — regression | `5fb09aa4…` | **passed** (exit 0) | 1 pass |
| Verification — baseline | `fae0e1d9…` | **passed** (exit 0) | 5 pass |

Verdict: **`verified_for_tested_scenarios`**

### RC-002 and RC-003 — Scenario 2 (batch atomicity and source-identity semantics)

Scenario 2 ran two findings against the already-repaired application
(snapshot `a0efceb7…`), sharing one protected manifest and one baseline
verification execution.

#### RC-002 — Batch atomicity (AC-007)

**Finding:** `import_records()` must roll back all newly inserted rows if any
record in the batch fails.  The application used a bare list comprehension with
per-record `conn.commit()` calls — a failure at record N left records 1…N-1
permanently committed.

**Repair:** wrapped `import_records()` in a `BEGIN / ROLLBACK / COMMIT`
envelope; removed the per-record `conn.commit()` from `insert_line_item()`.

**Evidence:** [`runs/rc-002/evidence-rc002.json`](runs/rc-002/evidence-rc002.json)
| [`runs/rc-002/report-rc-002.md`](runs/rc-002/report-rc-002.md)

| Phase | Execution ID | Outcome | Tests |
|---|---|---|---|
| Reproduction | `07b5f2b6…` | **failed** (exit 1) | 1 failure |
| Verification — regression | `2bc00fd9…` | **passed** (exit 0) | 1 pass |
| Verification — baseline | `81715fe2…` | **passed** (exit 0) | 5 pass |

Verdict: **`verified_for_tested_scenarios`**

#### RC-003 — Source-identity semantics (AC-004 / AC-005 / AC-006)

**Finding:** `import_record()` called `insert_line_item()` unconditionally with
no prior SELECT and no UNIQUE constraint on `source_record_id`.
Identical replays created duplicate rows (AC-004 violated).
Conflicting re-imports were silently accepted as a second row (AC-005 violated).
AC-006 (distinct `source_record_id` values with identical business fields must
both be stored) was already compliant — its test serves as a regression guard.

**Repair:** added `_check_source_identity()` pre-INSERT gate implementing the
exact-replay and conflict semantics; added `get_line_item_by_source_id()` to
[`sample_app/database.py`](sample_app/database.py).

**Evidence:** [`runs/rc-002/evidence-rc003.json`](runs/rc-002/evidence-rc003.json)
| [`runs/rc-002/report-rc-003.md`](runs/rc-002/report-rc-003.md)

| Phase | Execution ID | Outcome | Tests |
|---|---|---|---|
| Reproduction | `7de07b54…` | **failed** (exit 1) | 2 failures, 1 guard pass |
| Verification — regression | `8fc097e1…` | **passed** (exit 0) | 3 pass |
| Verification — baseline | `81715fe2…` | **passed** (exit 0) | 5 pass |

Verdict: **`verified_for_tested_scenarios`**

---

## Bob-only control comparison

As a control, AC-001 was also addressed using Bob IDE without the RealityCheck
workflow — a direct conversational repair with no structured checkpoints.
The control correctly identified and fixed the `str(int(…))` coercion in a
single pass, and the existing test suite passed.

**What the Bob-only control achieved:** a correct, cheap fix to AC-001.
It is not claimed to be slower or faster than RealityCheck — no timing
comparison was recorded.

**What the Bob-only control did not produce:**

- No explicit developer acceptance checkpoint — the interpretation of the
  requirement and the proposed test were not formally reviewed before the repair.
- No protected inputs — no mechanism prevented the contract document, the test
  file, or the fixtures from being modified as part of the repair.
- No reproducible execution history — there is no reproduction execution that
  demonstrates the defect existed before the repair.
- No bounded repair record — application snapshots and a structured patch were
  not recorded.
- No auditable evidence chain — no evidence JSON, no verdict from a
  deterministic runner, no linked execution artifacts.

**Summary:** the Bob-only control solved AC-001 correctly and more cheaply.
RealityCheck added structured acceptance, protected inputs, reproducible
execution history, bounded repair, and auditable evidence — at the cost of
additional workflow overhead and token usage.

---

## Limitations

- `verified_for_tested_scenarios` means only the specific counterexample
  scenarios in the accepted regression tests were executed and passed.
  It does not mean the application is free of other defects, fully verified
  against all contract requirements, or production-safe.
- AC-002 and AC-003 have no independent regression tests in the current runs.
- All counterexample inputs are synthetic and contract-derived; they are not
  drawn from the UCI Online Retail dataset.
- The AC-005 exception interface (`ValueError` mentioning `source_record_id`)
  is a developer-accepted interface decision, not uniquely determined by the
  contract text.
- The workflow does not cover requirements marked `ambiguous` — those require
  developer resolution before RealityCheck can proceed.

---

## Install and run

Python 3.10 or later is required.

```bash
pip install -e ".[dev]"
```

Run the baseline tests:

```bash
pytest tests/existing/
```

Run the full regression suite:

```bash
pytest tests/existing/ tests/regression/
```

---

## Data provenance

Fixtures in `fixtures/` are **synthetic** development fixtures hand-authored
to exercise the application. They are not rows extracted from the UCI Online
Retail dataset. See [`docs/source-notes.md`](docs/source-notes.md) for details.
