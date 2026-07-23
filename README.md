# JA-ES — Judgment Assurance Evidence Schema v0.6

![verify](https://github.com/judgmentassurance/ja-es/actions/workflows/verify.yml/badge.svg)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21501112.svg)](https://doi.org/10.5281/zenodo.21501112)

Machine-readable specification for evidence of human judgment over AI-mediated
consequential decisions.

**Status: draft for review. Validated against the bundled reference implementation and interactive demo; not yet validated in a production workflow.**

## The three record types

The `judgment_record` implements the Minimum Control Standard's individual-decision evidence requirements. The `governance_judgment_record` and `auto_execution_log` are JA-ES extensions that support the framework beyond that minimum. See [CONFORMANCE.md](CONFORMANCE.md).

| Type | What it evidences |
|---|---|
| `judgment_record` | The evidentiary output of a completed Atomic Unit at an individual decision: a human accepted, modified, rejected, escalated or deferred an AI output, with structured reasoning and named ownership. |
| `governance_judgment_record` | The evidentiary output of a completed Atomic Unit at the Governance layer: a named person decided a defined population may proceed *without* contemporaneous human review, and recorded why. |
| `auto_execution_log` | A decision executed inside such a boundary, linked by id and hash to the governance judgment that authorized it, with per-condition proof and an explicit record of the action actually executed. |

A `judgment_record` may also carry `boundary_evaluation` — evidence that the machine evaluated this recorded decision against the boundary, it **failed**, and it was routed to a human. That is the inverse of `authorizing_boundary`. Population completeness still requires independent Guard reconciliation.

Every governance boundary separately states **when** automation may act and
**which actions** it may execute. Every Auto-Execution Log separately records
the AI's `recommended_action` and the system's `executed_action`; `verify.py`
confirms that they match and that the executed action was permitted by the
sealed governance boundary.

An Atomic Unit is the control event. A Judgment Record is the evidence it
produces. An Auto-Execution Log is not the product of a contemporaneous Atomic
Unit — it evidences the application of an earlier institutional judgment, and
carries a verifiable link back to it.

## Contents

| File | What it is |
|---|---|
| `JA-ES-v0.6-specification.md` | Read first. Plain-English spec and rationale. |
| `evidence-record.schema.json` | The three append-only and tamper-evident record types. |
| `linked-event.schema.json` | Post-decision events: outcomes, corrections, probe evaluations. |
| `examples/` | Eight valid records, hashes computed and chains verified. |
| `test-invalid/` | 44 records that MUST fail schema validation. |
| `test-integrity/` | 7 records that are schema-valid but MUST fail verification. |
| `test-action-verification/` | Three sealed, schema-valid scenarios that MUST fail cross-record action verification. |
| `verify.py` | Reference verifier: schema + hashes + chains + cross-record links. |
| `build_examples.py` | Reference implementation of the hashing and chaining rules. |
| `guard-prototype/` | Separate JA Guard population-reconciliation prototype: schema, retained manifests, a worked exception case and its verifier. It is deliberately not a fourth JA-ES record type. |
| `CHANGELOG.md` | Version history. Published versions are never overwritten. |
| `LICENSE` | CC BY 4.0; trademark and conformance terms. |

## For non-technical readers

Open any file in `examples/` in a text editor — they read as plain text.

- `example-1-governance-boundary-original.json` — a VP establishes an
  auto-approval band at score 720.
- `example-2-governance-boundary-narrowed.json` — nine months later the same
  VP narrows it to 740 after cohort data shows 1.9% delinquency in the 720–739
  band versus 0.7% above it. It names the boundary it replaces, by hash.
- `example-5-auto-execution-log.json` — one $6,000 loan approved with no human
  in the loop, pointing back to that boundary, showing all eligibility
  conditions it satisfied, and recording that `approve` was both recommended
  and actually executed.
- `example-4-boundary-failed-routed-to-human.json` — the other side: an
  application scoring 739, one point under the new floor, that the machine
  refused to auto-execute and sent to an analyst, who approved it anyway. The
  record shows exactly which condition failed.

Read in that order, those four files are the argument: nobody reviewed the
$6,000 loan, and the organization can still say exactly who authorized it, when,
on what evidence, and that the loan fell inside what was authorized — and for
the one the machine would not touch, exactly why it went to a human and what
that human did with it.

## Verifying

    pip install jsonschema rfc8785
    python verify.py examples/

Expected: `PASSED — schema valid, all hashes verify, chains intact, all
cross-record links resolve.`

To confirm your tooling actually enforces the standard:

    python verify.py test-integrity/     # must FAIL — tampered records
    python verify.py test-action-verification/  # must FAIL — all 3 scenarios

Every file in `test-invalid/` must fail schema validation. Every file in
`test-integrity/` **passes** schema validation and must fail verification.
Each subdirectory in `test-action-verification/` must also fail `verify.py`
despite valid schema, hashes and chains, because the action was unpermitted,
the recommendation and execution differ, or the permitted set was substituted.

### Running the separate Guard prototype

JA-ES verifies the records that exist; it cannot prove that every decision that
should have produced a record actually did. The separate Guard prototype tests
that population-completeness problem:

    python guard-prototype/verify_reconciliation.py

Expected: `VERIFICATION PASSED` after reporting that reconciliation itself
**failed** with 3 missing and 3 orphan records. Evaluated and recorded counts
are both 3,412, so an arithmetic count would have passed. The retained identity
manifests expose the offsetting omissions and orphans.

This is not contradictory. The failed reconciliation is the control finding;
the passed verification means the control operated, reported the finding
honestly, and can be reproduced from retained manifests. Verification asks
whether the assurance artifact is truthful and reproducible—not whether the
underlying population happened to contain no exceptions.

## Validator portability

The schemas are valid JSON Schema draft 2020-12 and validate under Python
`jsonschema`. Ajv 8 requires `strict: false` (or `strictRequired: false`) to
compile them, because conditional subschemas apply `required` to properties
declared elsewhere in the document. This is a known Ajv strictness rule, not a
spec violation, but implementers should expect it.

## Important

Schema validation establishes that a record is well-formed. It does **not**
establish that the record is unaltered, that reasoning was sufficient, that a
boundary was appropriate, that ground truth was independent, or that the record
is truthful. The first of those is caught by `verify.py`; the rest require human
assessment. See "What the schema enforces, and what it cannot" in the
specification.

*Judgment Assurance (Kavalir, 2026). CC BY 4.0.*
