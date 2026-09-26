---
name: realitycheck
description: Use when the user wants to run the RealityCheck workflow — converts documented application requirements into reproducible, reviewable repair evidence by investigating implementation assumptions, generating candidate regression tests, reproducing failures, applying bounded repairs after developer acceptance, and verifying unchanged checks with deterministic tooling.
---

# RealityCheck Workflow

RealityCheck turns a contract/application mismatch into a complete, auditable evidence chain:

```
Requirement
↓
Implementation assumption
↓
Counterexample
↓
Developer-accepted regression test
↓
Reproduced original failure
↓
Bounded application repair
↓
Unchanged verification inputs
↓
Observed verification result
```

**Core principle:** a model claim is not verification.
Bob reasons about the application; deterministic execution via `realitycheck.runner` determines whether tests actually pass or fail.

---

## Stage 1 — Establish baseline

Before investigating any suspected defect:

1. Read `docs/application-contract.md` — identify every stated requirement.
2. Read `docs/source-notes.md` — note the data provenance and any publisher conventions.
3. Read `fixtures/manifest.json` — identify fixture provenance labels.
4. List `tests/existing/` — identify the current baseline test suite.
5. Inspect the most recent run under `runs/` for a recorded baseline execution, **or** run one now:

   ```python
   from realitycheck.runner import run_pytest
   execution = run_pytest(
       repo_root=".",
       pytest_targets=["tests/existing"],
       run_id="<run_id>",
       phase="baseline",
   )
   ```

6. Report whether existing tests are currently passing.

**Do not treat passing existing tests as proof that every contract requirement is satisfied.**

---

## Stage 2 — Independent investigation (parallel)

Spawn two read-only subagent investigators when the investigation is non-trivial.
Do not spawn subagents for trivial single-step lookups.

### Investigator A — Requirements and data

Provide these read-only access to:

- `docs/application-contract.md`
- `docs/source-notes.md`
- `fixtures/`

Expected output per finding candidate:

```
requirement_id
requirement_text
classification        (documented | inferred | ambiguous)
source                (file path or document name)
locator               (section heading, line range, or anchor)
relevant_counterexample_candidate
ambiguities
```

### Investigator B — Implementation

Provide these read-only access to:

- `sample_app/`
- Any investigation fixtures referenced by Investigator A

Expected output per candidate:

```
assumption
code_artifact
symbol
behavior
possible_requirement_mismatch
```

**Both investigators must be read-only.**
Do not have multiple agents modify application files.

---

## Stage 3 — Synthesize findings

The parent agent compares both investigation results and constructs a structured claim for each candidate mismatch:

```
requirement_id
requirement_text
classification        (documented | inferred | ambiguous)
source
locator
implementation_assumption
code_artifact
symbol
counterexample
expected_behavior
proposed_regression_test_description
ambiguities
```

**Classification rules:**

- `documented` — requirement is stated explicitly in `docs/application-contract.md`.
- `inferred` — behavior is implied but not stated; requires caution.
- `ambiguous` — sources conflict or the requirement is unclear.

A finding must not become a confirmed defect merely because code looks suspicious.

If the requirement is `ambiguous` or sources conflict:
- Mark the finding as `ambiguous`.
- Do **not** proceed to repair.
- Present the ambiguity to the developer for resolution first.

If no credible mismatch is found, conclude:

```
No reproduced defect found.
```

and stop. Do not force a finding merely because RealityCheck was invoked.

---

## Stage 4 — Human acceptance checkpoint (STOP)

**Stop here. Do not modify any file.**

Present the proposed finding to the developer with:

1. **Requirement** — exact text and source reference from the contract.
2. **Classification** — `documented`, `inferred`, or `ambiguous`.
3. **Implementation assumption** — what the code appears to assume.
4. **Counterexample** — a minimal concrete input that exercises the mismatch.
5. **Expected behavior** — what the contract requires.
6. **Candidate regression test** — test code (not yet written to disk) that:
   - tests externally observable behavior (e.g., persisted/retrieved values);
   - verifies the required behavior, not merely absence of an exception;
   - uses the minimal counterexample;
   - is expected to fail on the unmodified application for the stated reason.

Ask the developer explicitly:

> Do you accept this requirement interpretation, counterexample, and candidate regression test?
> Reply with ACCEPT to proceed, or provide corrections.

**Do not interpret silence or ambiguous replies as acceptance.**

If the developer rejects or modifies the finding:
- revise accordingly;
- re-present before proceeding.

If the developer resolves an ambiguity, update the classification accordingly.

---

## Stage 5 — Write the accepted regression test

Only after explicit `ACCEPT`:

1. Write the accepted regression test to:

   ```
   tests/regression/<test_file>.py
   ```

2. Do not modify any other file at this step.

**Regression test requirements:**

- Test externally observable behavior.
- Represent the accepted requirement faithfully.
- Use a minimal counterexample.
- Verify the expected persisted/retrieved value — not merely the absence of an exception.
- Must fail on the unmodified application for the stated reason.

A test that fails because of syntax errors, missing imports, test-framework errors, malformed fixtures, or incorrect setup does **not** reproduce an application defect. Fix those issues before proceeding.

---

## Stage 6 — Freeze verification inputs

After writing the accepted regression test, use the deterministic RealityCheck tooling to create the protected manifest:

```python
from realitycheck.runner import create_protected_manifest

protected_paths = [
    "docs/application-contract.md",
    "docs/source-notes.md",
    "fixtures/manifest.json",
    # include any accepted fixture files explicitly
    "tests/existing/test_happy_path.py",
    "tests/regression/<accepted_test_file>.py",
    "pyproject.toml",
    "realitycheck/runner.py",
    "realitycheck/evidence.schema.json",
]

create_protected_manifest(
    repo_root=".",
    paths=protected_paths,
    output_path="runs/<run_id>/protected-manifest.json",
)
```

Record the manifest path in the evidence record.

**Application code under `sample_app/` is intentionally excluded — it is the repair target.**

Never silently regenerate protected hashes after application repair.
If protected-manifest verification fails at any later stage, the verdict is immediately `blocked`.

---

## Stage 7 — Reproduce before repair

Before changing application code:

1. Snapshot the current `sample_app/`:

   ```python
   from realitycheck.runner import snapshot_application
   base_snapshot = snapshot_application("sample_app/")
   ```

2. Run the accepted regression test using `realitycheck.runner` with phase `reproduction`:

   ```python
   from realitycheck.runner import run_pytest
   repro_execution = run_pytest(
       repo_root=".",
       pytest_targets=["tests/regression/<accepted_test_file>.py::<test_node_id>"],
       run_id="<run_id>",
       phase="reproduction",
       protected_manifest_path="runs/<run_id>/protected-manifest.json",
   )
   ```

3. Inspect the result.

The finding may be classified as **reproduced** only when:

- the accepted test executed (not collected-but-skipped, not collection error);
- it failed for the stated application behavior reason (not a test infrastructure issue);
- protected inputs remain intact.

**Preserve this reproduction execution permanently. Do not overwrite it after repair.**

If reproduction fails for unexpected reasons (wrong error, collection error, skipped):
- investigate why before proceeding;
- fix the test if the issue is test infrastructure;
- do not proceed to repair until the intended failure is observed.

---

## Stage 8 — Bounded repair

Only after a successful reproduction:

Apply the smallest repair to `sample_app/` that:

- satisfies the accepted behavior described by the regression test;
- preserves all existing behaviors tested by `tests/existing/`.

**Repair boundary:**

```
sample_app/    ← only this directory may be modified
```

**Never modify during repair:**

- `docs/application-contract.md`
- `tests/existing/`
- `tests/regression/<accepted_test_file>.py`
- any accepted fixture
- `realitycheck/runner.py`
- `realitycheck/evidence.schema.json`
- `runs/<run_id>/protected-manifest.json`
- `pyproject.toml`

If repair appears to require modifying a protected input:
- **stop**;
- explain to the developer why modification seems necessary;
- do not proceed silently.

Prefer the minimal change. Avoid introducing unrelated refactors or new behaviors.

---

## Stage 9 — Verification

After repair:

1. **Verify the protected manifest** — run `verify_protected_manifest` and check `ok == True`. If `ok == False`, the verdict is `blocked` immediately.

2. **Snapshot the repaired application** — record the candidate snapshot id.

3. **Execute the regression test** with phase `verification`:

   ```python
   verif_regression = run_pytest(
       repo_root=".",
       pytest_targets=["tests/regression/<accepted_test_file>.py::<test_node_id>"],
       run_id="<run_id>",
       phase="verification",
       protected_manifest_path="runs/<run_id>/protected-manifest.json",
   )
   ```

4. **Execute the baseline suite** with phase `verification`:

   ```python
   verif_baseline = run_pytest(
       repo_root=".",
       pytest_targets=["tests/existing"],
       run_id="<run_id>",
       phase="verification",
       protected_manifest_path="runs/<run_id>/protected-manifest.json",
   )
   ```

5. **Inspect every execution** for:
   - collection errors (exit code 4 / zero tests collected);
   - skipped required tests;
   - failures or errors;
   - timeouts.

**Verification must NOT emit `verified_for_tested_scenarios` when:**

- protected-manifest verification fails;
- required tests were not collected or executed;
- pytest collection fails;
- required tests are skipped;
- any execution times out;
- the regression test fails;
- any baseline test fails;
- required artifacts are missing.

Use `realitycheck.runner.compute_verdict` for the deterministic verdict:

```python
from realitycheck.runner import compute_verdict
verdict = compute_verdict(
    reproduction_execution=repro_execution,
    verification_execution=verif_regression,
    protected_verification=manifest_verification_result,
)
```

Only if all checks pass may the verdict be:

```
verified_for_tested_scenarios
```

**Never claim:** `production_safe`, `fully verified`, or `bug free`.

---

## Stage 10 — Assemble evidence record

Construct a JSON record conforming to `realitycheck/evidence.schema.json`.

The record must preserve **both** the original reproduction execution and the post-repair verification execution — never replace historical evidence.

Required fields:

```json
{
  "schema_version": "1.0",
  "run_id": "<run_id>",
  "finding_id": "<finding_id>",
  "requirement": {
    "id": "<requirement_id>",
    "text": "<requirement_text>",
    "classification": "documented | inferred | ambiguous",
    "sources": [...]
  },
  "assumption": {
    "description": "<assumption>",
    "code_artifact": "<path>",
    "symbol": "<symbol>"
  },
  "counterexample": {
    "kind": "input-record",
    "fixture": "<path>",
    "record_ids": [...],
    "expected_behavior": "<description>"
  },
  "acceptance": {
    "decision": "accepted",
    "reviewer": "<developer>",
    "timestamp": "<iso8601>",
    "protected_manifest": "runs/<run_id>/protected-manifest.json"
  },
  "regression": {
    "test_artifact": "tests/regression/<file>.py",
    "node_ids": [...],
    "expected_failure": "<description>"
  },
  "executions": {
    "reproduction": {
      "execution_id": "<id>",
      "phase": "reproduction",
      "outcome": "failed",
      "artifact_dir": "runs/<run_id>/<execution_id>"
    },
    "verification": {
      "execution_id": "<id>",
      "phase": "verification",
      "outcome": "passed",
      "artifact_dir": "runs/<run_id>/<execution_id>"
    }
  },
  "repair": {
    "base_snapshot": "<snapshot_id>",
    "candidate_snapshot": "<snapshot_id>",
    "patch": "<unified diff>"
  },
  "verdict": {
    "status": "verified_for_tested_scenarios",
    "reason": "<reason>",
    "limitations": [
      "Verdict covers only the tested scenarios — not all contract requirements."
    ]
  }
}
```

Write to:

```
runs/<run_id>/evidence.json
```

---

## Stage 11 — Generate report

Use `realitycheck/report.py` to produce the human-readable Markdown report:

```python
import json
from realitycheck.report import generate_report

evidence = json.loads(open("runs/<run_id>/evidence.json").read())
report_md = generate_report(evidence)
open("runs/<run_id>/report.md", "w").write(report_md)
```

The report must clearly distinguish:

**Model interpretation** (labelled as such):
- requirement interpretation
- identified implementation assumption
- proposed relationship between code and requirement

**Deterministic observations** (labelled as such):
- executed pytest node IDs
- exit codes
- pass / fail / error / timeout
- protected-manifest status
- application snapshot IDs

The report must not use an LLM to determine whether execution succeeded.

---

## Controls and uncertainty

The workflow allows Bob to conclude:

```
No reproduced defect found.
```

Do not force a finding merely because RealityCheck was invoked.

If evidence is insufficient or a stage cannot be completed cleanly, the verdict is `blocked`.
Retain `candidate` or `ambiguous` status rather than fabricating a result.

Avoid confirmation bias: code that looks suspicious is not a confirmed defect.

---

## Scope discipline

RealityCheck is not:

- a generic linting agent
- a generic code-review bot
- a generic chatbot
- an arbitrary security scanner
- a production certification system

Its specific purpose is:

> Turning contract/application mismatches into reproducible, reviewable repair evidence.

---

## Quick reference — `realitycheck` module

```python
from realitycheck.runner import (
    sha256_file,
    create_protected_manifest,
    verify_protected_manifest,
    snapshot_application,
    run_pytest,
    compute_verdict,
)
from realitycheck.report import generate_report
```

All verdict logic is deterministic. No LLM is called by these functions.
