# RealityCheck — Hackathon Evaluation

This document evaluates the RealityCheck prototype against the eight evaluation
criteria established for the hackathon submission.  All claims are grounded in
the recorded evidence in `runs/`.  No productivity, speed, or cost comparisons
are made unless supported by recorded measurements.

---

## 1. The developer workflow problem RealityCheck addresses

Large or legacy codebases accumulate requirements in documents — contracts,
specifications, README files — that do not automatically stay in sync with the
implementation.  When a developer or AI assistant suspects a discrepancy, the
typical outcome is:

- an informal code review producing an opinion ("the code looks wrong here");
- an ad-hoc fix that may or may not be bounded to the affected behaviour;
- no reproducible record of what the application did before the fix.

This leaves several open questions that cannot be answered after the fact:

1. Was the requirement interpretation correct, and did a human agree?
2. Did the application actually fail the requirement before the fix?
3. Was the fix minimal and confined to application code?
4. Does the application pass the requirement after the fix, against unchanged
   inputs?

RealityCheck addresses this gap by turning a contract/application mismatch into
a complete, auditable evidence chain: requirement → human-accepted regression
test → reproduced failure → bounded repair → deterministic verification.

---

## 2. How RealityCheck uses IBM Bob IDE

RealityCheck is implemented as a **Bob skill** — a structured instruction set
loaded into Bob's context that guides it through a fixed eleven-stage workflow.

### Skills
The skill (`SKILL.md`) encodes the complete workflow protocol: stage ordering,
acceptance gate language, evidence schema, repair boundary rules, and verdict
conditions.  The skill instructs the workflow; specific verification invariants
— protected-manifest integrity, per-node reproduction status, and post-repair
pass requirements — are enforced deterministically by
`realitycheck.runner.compute_verdict`, which blocks rather than emits
`verified_for_tested_scenarios` if any invariant is not satisfied.

### Parallel investigation via subagents
At Stage 2, Bob spawns two independent read-only subagents simultaneously:

- **Investigator A** is given access to `docs/` and `fixtures/` only.  It
  identifies requirement candidates, classifies them (`documented` /
  `inferred` / `ambiguous`), and cites sources verbatim.
- **Investigator B** is given access to `sample_app/` only.  It identifies
  implementation assumptions and potential mismatches.

The parent Bob agent synthesises both outputs.  Neither subagent modifies any
file.  This parallel structure separates the requirements reading from the code
reading, reducing the risk of confirmation bias.

### Human acceptance checkpoint
At Stage 4, the workflow **stops unconditionally**.  Bob presents:

- the exact requirement text and its source location in the contract;
- the classification (`documented`, `inferred`, or `ambiguous`);
- the implementation assumption and the code symbol involved;
- the proposed counterexample (minimal input that exercises the mismatch);
- the candidate regression test (not yet written to disk).

Baseline executions and their artifacts may be written before this checkpoint
to establish a passing baseline.  Candidate regression tests are neither
written to disk nor frozen until after the developer replies `ACCEPT`;
repair evidence is likewise gated by acceptance.

The acceptance decision, reviewer identity, and timestamp are recorded in the
evidence JSON.  In every completed run in this repository, the reviewer is
recorded as `"developer (explicit ACCEPT reply)"`.

### Agent-driven repair
At Stage 8, Bob applies the smallest change to `sample_app/` that satisfies
the accepted regression test.  The repair scope is described by the skill
instructions — protected inputs, test files, and the contract document must
not be modified.  The boundary is enforced deterministically by
`realitycheck.runner`: protected-manifest verification records SHA-256 hashes
of every protected file before and after repair; any modification causes
`compute_verdict` to block rather than emit `verified_for_tested_scenarios`.
The before and after states of `sample_app/` are recorded as SHA-256
directory-tree snapshots.

### Deterministic verification
At Stage 9, Bob calls `realitycheck.runner.run_pytest` and
`realitycheck.runner.compute_verdict`.  These functions invoke pytest as a
subprocess (no `shell=True`), parse the JUnit XML output, verify the protected
manifest, and emit a structured execution record.  No LLM judgment is applied
to determine whether a test passed or failed — Bob reads the structured record
and reports it.

---

## 3. How deterministic verification differs from model interpretation

Every RealityCheck evidence report (see `runs/*/report*.md`) is formatted with
two explicit label classes:

**Model interpretation** covers the reasoning steps that are inherently
model-authored: which contract clause is relevant, how the code appears to
diverge from it, what minimal input would expose the divergence.  These steps
are reviewed by a human developer and accepted before any executable artifact
is created.

**Deterministic observation** covers execution facts that are produced by
`realitycheck.runner` without LLM involvement: pytest exit codes, test
pass/fail/error counts, execution timestamps and durations, SHA-256 digests of
the application directory tree, and protected-manifest hash verification
results.

The verdict `verified_for_tested_scenarios` is produced by
`realitycheck.runner.compute_verdict`, which applies a fixed set of boolean
conditions to the execution record.  The model cannot claim a test passed; it
can only read a record that says so.

This separation means the evidence is independently checkable: someone can
re-run the accepted regression test against the recorded application snapshot
and observe the same result without involving Bob at all.

---

## 4. RC-001 — Simple end-to-end demonstration (Scenario 1)

**Requirement:** AC-001 — `invoice_no` is an opaque string identifier.  The
application must not apply integer coercion, padding removal, or any other
type-specific transformation.  A record imported with `invoice_no = "053636"`
must be retrievable by `invoice_no = "053636"` with the stored value equal
byte-for-byte.

**Source:** `docs/application-contract.md`, lines 10–24.

**Implementation assumption (model interpretation):** The `_normalize` function
in `sample_app/importer.py` applied `str(int(record["invoice_no"]))`.  This
coerces the string to an integer and back, silently stripping any leading zero.
For `"053636"` the stored value would be `"53636"`.

**Counterexample (model interpretation):** Import a record with
`source_record_id = "rc-001"` and `invoice_no = "053636"`.  A subsequent lookup
for `"053636"` must return exactly one row with `invoice_no == "053636"`.

**Accepted regression test:**
`tests/regression/test_rc001_invoice_no_preservation.py::test_leading_zero_invoice_no_preserved`

**Reproduced failure (deterministic observation):**
Execution `df96ba74…` — exit code 1, outcome `failed`, 1 test failure.
AssertionError: `Lookup by original invoice_no='053636' returned no rows.`

**Repair:** one-line change — `str(int(…))` → `str(…)` in `_normalize`.
Base snapshot: `3e7416b5…`.  Candidate snapshot: `a0efceb7…`.

**Verification (deterministic observation):**
- Regression test `5fb09aa4…` — exit 0, 1 pass. Protected manifest verified.
- Baseline suite `fae0e1d9…` — exit 0, 5 pass. Protected manifest verified.

**Verdict:** `verified_for_tested_scenarios`

RC-001 demonstrates the full end-to-end chain for the simplest case: a single
documented requirement, a single code symbol, a one-line repair, and a single
regression test.

---

## 5. Scenario 2 — Multi-constraint demonstration

Scenario 2 covered four interrelated contract requirements (AC-004, AC-005,
AC-006, AC-007) producing two findings (RC-002 and RC-003) that required
coordinated repairs to the same files.  Both findings share one protected
manifest (`runs/rc-002/protected-manifest.json`) and one baseline verification
execution (`81715fe2…`).

The pre-Scenario-2 baseline confirmed the application was in snapshot
`a0efceb7…` before either finding was addressed (runs `15884e67…` and
`31f307cd…`).

### RC-002 — Batch atomicity (AC-007)

**Contract requirement:** `import_records()` must be atomic.  If any record in
a batch fails, no records newly inserted by that batch may remain persisted.

**Defect reproduced:** `import_records()` was a bare list comprehension over
`import_record()` calls.  `insert_line_item()` committed after every individual
INSERT.  A `KeyError` on the third record left the first two records
permanently committed.

Counterexample: three records `batch-new-001`, `batch-new-002`, `batch-bad-003`
(missing `unit_price`) imported together.  After the error, both new records
remained in storage — AC-007 violated.

Reproduction execution `07b5f2b6…`: exit 1, 1 failure.
`AssertionError: AC-007 violated — 2 record(s) from the failed batch remain
persisted: ['batch-new-001', 'batch-new-002']`

**Repair:** added `BEGIN / ROLLBACK / COMMIT` transaction envelope to
`import_records()`; removed the per-record `conn.commit()` from
`insert_line_item()`.

Verification `2bc00fd9…`: exit 0, 1 pass.

### RC-003 — Source-identity semantics (AC-004 / AC-005 / AC-006)

Three related requirements were addressed together because they all concern how
the application handles repeated or conflicting `source_record_id` values:

- **AC-004 (exact replay safety):** re-importing the same `source_record_id`
  with identical contents must not create a second row.
- **AC-005 (source identity conflict):** re-importing an existing
  `source_record_id` with different contents must raise a clear error and leave
  the original row unchanged.
- **AC-006 (business-field duplicates):** two records with distinct
  `source_record_id` values must both be stored even if all business fields are
  identical.  This was **already compliant** on the unmodified application;
  its regression test is a guard only.

The AC-005 ambiguity (which exception type?) was resolved by developer
acceptance: `ValueError` with `"source_record_id"` in the message.  This
decision is recorded in `evidence-rc003.json` field
`acceptance.ac005_exception_type_decision`.

Reproduction execution `7de07b54…`: exit 1, 2 failures (AC-004 and AC-005),
1 pass (AC-006 guard).

**Repair:** added `get_line_item_by_source_id()` to `sample_app/database.py`;
added `_check_source_identity()` and the `_ExactReplay` sentinel class to
`sample_app/importer.py`; wired the check into `import_record()` before the
INSERT.  The transaction envelope added by RC-002 was preserved unchanged.

Verification `8fc097e1…`: exit 0, 3 pass.

### What Scenario 2 demonstrates beyond RC-001

- **Replay safety:** the idempotency requirement (AC-004) requires looking up
  an existing record before inserting — a non-trivial behavioural addition.
- **Identity conflicts with data preservation:** AC-005 requires the original
  row to survive the failed re-import — verifiable only by reading back the
  stored value after the error.
- **Preservation behaviour:** AC-006 requires that business-field equality does
  not suppress storage — verifiable by reading back two rows.
- **Batch atomicity:** AC-007 requires transactional rollback across multiple
  records — verifiable only by checking row counts after a partial failure.
- **Coordinated repair:** RC-002 and RC-003 touched overlapping code in the
  same files; the shared protected manifest ensured verification inputs were
  unchanged across both findings.

---

## 6. Bob-only control comparison

As a control, AC-001 was also addressed using Bob IDE in a direct conversational
repair — no RealityCheck skill, no structured workflow.

**What the control achieved:**
- Correctly identified the `str(int(…))` coercion as the defect.
- Applied the one-line fix to `sample_app/importer.py`.
- The existing five-test baseline suite passed after the fix.

**What the control did not produce:**
- No explicit acceptance checkpoint.  The requirement interpretation and test
  design were not presented to the developer for review before the fix.
- No protected inputs.  Nothing prevented the contract document, existing
  tests, or fixtures from being modified as part of the repair.
- No reproduction execution.  There is no recorded execution demonstrating the
  defect existed before the fix.
- No snapshot record.  The before/after state of `sample_app/` was not
  captured as a SHA-256 digest.
- No evidence JSON.  No structured record conforming to the evidence schema
  exists for the control run.
- No deterministic verdict.  `compute_verdict` was not called; the outcome
  rests on the model's assertion that the test passed.

**Summary:** the Bob-only control solved AC-001 correctly and more cheaply.
RealityCheck added structured acceptance, protected inputs, reproducible
execution history, bounded repair, and auditable evidence — at the cost of
additional workflow overhead and higher Bobcoin consumption.

No claim is made that RealityCheck is faster, more accurate, or cheaper than
the Bob-only approach for this class of defect.  The control demonstrates that
for a simple, clearly-specified requirement with a single-line fix, a direct
conversational repair is a valid and lower-cost option.  RealityCheck's value
is the auditable evidence chain, not the repair itself.

---

## 7. Bobcoin usage and measured observations

**Bobcoin** is Bob IDE's task-level usage metric.  It is not a token count
and it is not a monetary cost — it is the unit displayed in the Bob IDE task
summary panel at the end of a session.  Bob IDE records a Bobcoin value per
task; these values are available from the task-session summary screenshots in
`bob_sessions/`.

### Recorded Bobcoin values (from task-session summary screenshots)

| Screenshot | Task ID (prefix) | Description | Bobcoins | Notes |
|---|---|---|---|---|
| `01_initial_build_summary.png` | `35313e…` | Initial application and tooling build | ♾ 4.18 | Final summary |
| `02_rc001_realitycheck_summary.png` | `ace50b…` | RC-001 RealityCheck — investigation through acceptance checkpoint | ♾ 2.43 | **Intermediate screenshot** — task was intentionally paused at the human acceptance gate; this value does not represent the full task cost |
| `03_ac001_control_summary.png` | `853076…` | Bob-only control (AC-001, no RealityCheck workflow) | ♾ 0.607 | Final summary |
| `04_report_renderer_summary.png` | `01c83a…` | Report renderer development | ♾ 1.23 | Final summary |
| `05_scenario2_baseline_summary.png` | `ee8849…` | Scenario 2 baseline execution setup | ♾ 0.301 | Final summary |
| `06_scenario2_realitycheck_summary.png` | `df985e…` | Scenario 2 RealityCheck (RC-002 and RC-003) | ♾ 5.16 | Final summary |
| `07_evaluation_documentation_summary.png` | `6583b3…` | Evaluation documentation (README and docs/evaluation.md) | ♾ 3.51 | Final summary |

### Observations

- The Bob-only control task (`853076…`, ♾ 0.607) consumed fewer Bobcoins than
  either RealityCheck finding task (RC-001 at ♾ 2.43 and Scenario 2 at ♾ 5.16).
  The Scenario 2 baseline setup task (`ee8849…`, ♾ 0.301) is cheaper than the
  control; it is a short infrastructure task rather than a full finding run.
  This is consistent with the control producing no structured evidence chain,
  no subagent investigation, no protected-manifest operations, and no
  multi-phase execution runs.
- The RC-001 RealityCheck value (♾ 2.43) reflects only the
  investigation-through-acceptance portion of that session.  The full task
  cost after repair, verification, evidence assembly, and report generation is
  not available as a single final-summary figure and is therefore not stated.
- Scenario 2 (♾ 5.16) covers two findings (RC-002 and RC-003), four
  regression tests (1 for RC-002, 3 for RC-003), and five execution phases,
  which is consistent with it being the highest single-task Bobcoin value
  among the completed sessions.

### What is not claimed

- No per-finding breakdown of Bobcoin consumption is available from the
  recorded screenshots.
- No claim is made about developer time saved or added by the workflow.
- No claim is made that RealityCheck is more cost-effective than the Bob-only
  approach.  The Bob-only control solved AC-001 correctly at lower Bobcoin cost;
  RealityCheck produced an auditable evidence chain at higher Bobcoin cost.

### Recorded pytest execution times (from execution.json artifacts)

These are subprocess wall-clock durations for pytest runs only — they are not
Bob session durations and are unrelated to Bobcoin consumption.

| Run | Phase | Execution ID | Duration (ms) |
|---|---|---|---|
| baseline-001 | baseline | exec-baseline-001 | 363 |
| rc-001 | reproduction | df96ba74… | 547 |
| rc-001 | verification (regression) | 5fb09aa4… | 437 |
| rc-001 | verification (baseline) | fae0e1d9… | 286 |
| rc-002 | reproduction | 07b5f2b6… | 470 |
| rc-002 | verification (regression) | 2bc00fd9… | 430 |
| rc-002 | reproduction | 7de07b54… | 394 |
| rc-002 | verification (regression) | 8fc097e1… | 358 |
| rc-002 | verification (baseline, shared) | 81715fe2… | 297 |
| rc-002-pre | baseline | 15884e67… | 367 |
| rc-002-pre | baseline | 31f307cd… | 445 |

---

## 8. Limitations and what `verified_for_tested_scenarios` means

### What `verified_for_tested_scenarios` means

The verdict `verified_for_tested_scenarios` means all of the following were
observed to be true at the time of the verification execution:

1. The protected manifest was verified — all protected files (contract, source
   notes, fixture manifest, accepted tests, `pyproject.toml`, runner) were
   present and their SHA-256 hashes matched the recorded values.
2. The accepted regression test was collected (not skipped, not a collection
   error) and the test passed (exit code 0, zero failures).
3. The existing baseline suite was collected and all five tests passed.

**What it does not mean:**

- It does not mean the application satisfies every clause of
  `docs/application-contract.md`.  AC-002 and AC-003 have no independent
  regression tests in the current runs.
- It does not mean the application is free of defects not covered by the
  tested scenarios.
- It does not mean the application is production-safe.
- It does not mean the counterexample inputs are representative of real
  production data.  All counterexample inputs are synthetic and
  contract-derived; none are drawn from the UCI Online Retail dataset.

### Other limitations

- **AC-005 interface decision:** the requirement that a source-identity conflict
  must "fail clearly" does not specify the exception type.  The developer
  accepted `ValueError` with `"source_record_id"` in the message as the
  interface contract.  A different caller might reasonably expect a different
  exception type.  This decision is recorded in the evidence but is not uniquely
  determined by the contract text.

- **Ambiguous requirements are not processed:** the workflow classifies
  requirements as `documented`, `inferred`, or `ambiguous`.  Ambiguous
  requirements halt the workflow; they cannot receive a verdict until the
  developer resolves the ambiguity.  The current runs cover only `documented`
  requirements.

- **Scope:** RealityCheck is not a generic linter, a security scanner, a
  full-coverage test generator, or a production certification system.  Its
  specific scope is: turning contract/application mismatches into reproducible,
  reviewable repair evidence, one finding at a time.

- **Single application, synthetic fixtures:** the prototype was demonstrated
  against one small SQLite application with hand-authored fixtures.
  Generalisation to other application types, persistence layers, or larger
  codebases has not been validated.

- **Bob-only control not instrumented:** the control run did not record token
  usage, session duration, or developer interaction count.  A rigorous
  comparison of workflow cost would require instrumenting both approaches on the
  same finding under controlled conditions.

---

## 9. Repair-to-checkpoint mapping

Each repair patch recorded in the evidence JSON corresponds to a Git checkpoint
(tag or commit) where the repaired application state is the HEAD.  Judges can
inspect the complete diff at any checkpoint without re-running the workflow.

| Finding | Evidence file | Patch field | Git tag / commit | Description |
|---|---|---|---|---|
| RC-001 | `runs/rc-001/evidence.json` | `repair.patch` | `rc001-verified` (`eb7cf86`) | RC-001 repair verified — `str(int(…))` → `str(…)` in `_normalize` |
| RC-002 | `runs/rc-002/evidence-rc002.json` | `repair.patch` | `rc002-verified` (`2eeacdc`) | RC-002 + RC-003 repairs verified — transaction envelope and source-identity gate |
| RC-003 | `runs/rc-002/evidence-rc003.json` | `repair.patch` | `rc002-verified` (`2eeacdc`) | Same commit — RC-003 repair is part of the Scenario 2 coordinated repair |

To inspect the RC-001 repair diff:

```bash
git diff scenario1-baseline rc001-verified -- sample_app/
```

To inspect the Scenario 2 (RC-002 + RC-003) repair diff:

```bash
git diff scenario2-baseline rc002-verified -- sample_app/
```

**Note on paths in execution artifacts:** the `runs/` directory contains 76
files total.  Of these, 11 are execution records (`execution.json`, one per
execution phase) and 33 files contain absolute workspace paths recorded at
run time on the original machine.  Many artifact references — `stdout.txt`,
`stderr.txt`, `junit.xml`, `application-snapshot.json`, and `environment.json`
— are stored as repository-relative paths in execution records and are fully
portable.  Absolute workspace paths appear in metadata and log *contents* —
specifically in fields such as `working_directory` within `environment.json`,
and in the `environment_manifest`, `stdout`, and `stderr` path values in some
older execution records — because those values were recorded as absolute paths
at run time.  They have not been rewritten.  Evidence JSON files, test files,
and source files referenced in evidence records use repository-relative paths.

