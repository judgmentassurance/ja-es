# JA-ES Conformance and Known Limitations

**Applies to:** JA-ES v0.6 (concept DOI 10.5281/zenodo.21501112)
**Status:** Draft for review.

## What a valid JA-ES record establishes, and what it does not

JA-ES is an evidence format. It structures and verifies evidence that a human exercised judgment over an AI-mediated decision. It is not, by itself, a determination that an organization has met the requirements of Judgment Assurance.

Judgment Assurance is defined by three instruments, in order of authority:

| Instrument | Role |
|---|---|
| **JA-MCS v1.0** (Minimum Control Standard) | Defines the minimum requirements for a claim of Judgment Assurance. |
| **JA Assessment and Evidence Guide v1.0** | Defines how operation of those requirements is tested. |
| **JA-ES** (this specification) | Supplies machine-readable evidence structures and reference verification. |

Guard evaluates the system and the population: completeness, pattern monitoring, drift, and corrective action.

A record that passes JA-ES schema validation and cryptographic verification is **schema-valid**. That is a statement about form and integrity. It is not a statement that the recorded judgment was sufficient, that the decision-maker held the authority they asserted, or that the organization is **JA-conformant**. Those conclusions are reached by a competent assessor under JA-MCS and the Guide. This document uses "schema-valid" or "JA-ES-valid" for the machine result and reserves "JA-conformant" for the organizational conclusion.

## Terminology

- The record types are **append-only and tamper-evident**, not immutable. JA requires that modification be detectable, not that records be metaphysically unchangeable.
- A `judgment_record` is the **evidentiary output of a completed Atomic Unit**, not the Atomic Unit itself. The Atomic Unit is the control event; the record is what it produces.
- A completed Atomic Unit resolves to one of three human dispositions: **accept, modify, or reject**. Escalation and deferral are legitimate workflow actions, but standing alone they do not resolve what the human did with the AI output, and they are not completed judgments.
- The **Governance Judgment Record** and the **Auto-Execution Log** are JA-ES extensions that support the framework. They are not artifacts required by JA-MCS v1.0.
- A Governance Judgment Record evidences the human judgment that approved or changed a reliance boundary within a JA Envelope. It is **not** the Envelope, and it does not replace the Envelope Register. The Envelope defines the workflow-level control design; the Governance Judgment Record evidences a decision made inside it.
- An **Auto-Execution Log** proves what authority was claimed and whether the recorded case satisfied that authority. It does not establish that the Envelope appropriately classified the case as eligible for automation, or that the organization satisfies JA-MCS. A governance boundary does not excuse the failure to route a case to a human where the Envelope requires one.

## Scope of the Guard prototype

The bundled reconciliation prototype covers **population completeness and chain anchoring only**. It demonstrates that a count-based check is insufficient: it reports missing and orphan records even when evaluated and recorded totals match. Full Guard additionally requires pattern monitoring, automation-bias detection, reasoning-quality review, threshold-drift detection, corrective action, and periodic Envelope review. The prototype is not the full Guard function.

## Known limitations in v0.6

These are disclosed deliberately. v0.6 is preserved unchanged as the citable artifact; the dispositions below are scoped for v0.7, the first expressly JA-MCS-filtered release.

| Item | v0.6 status | v0.7 disposition |
|---|---|---|
| Hash algorithm | Schema permits SHA-256, SHA-384, and SHA-512; the reference verifier computes SHA-256 only. | Restrict the schema to SHA-256, which the examples, demo, and verifier already implement. |
| Machine enforcement of workflow traceability | The specification describes workflow and reliance-standard fields as machine-enforced, but they are optional and unenforced. | Require workflow or an independently resolvable Envelope reference, and correct the enforcement claim. |
| Permitted-window timing | Records carry `decision_at` and `recorded_at`, and may carry the permitted window, but neither the schema nor the verifier compares them. | Require or resolve the window and have the verifier compare elapsed time against it; records outside it must be marked reconstructed. |
| Authority to act | Identity and role are captured; the basis for the person's authority is not. | Add an `authority_basis` or an Envelope-resolvable role reference. A string assertion cannot prove delegated authority; this remains subject to human verification. |
| Institutional-risk impact | The impact categories omit `institutional_risk`, which is within JA-MCS scope. | Add `institutional_risk`. The additional reputational and employment categories may remain as refinements. |
| Home for the sufficiency determination | An assessor's sufficiency determination is itself a judgment that must be recorded, but a `judgment_record` requires an AI output and has no clean place for it. | Add a linked assessment event, keeping the original contemporaneous record uncontaminated by later assessment. |
| Interim dispositions | `escalate` and `defer` are selectable as completed dispositions. | Restrict completed dispositions to accept, modify, or reject, or model interim workflow events separately. |

## The one line to keep in view

JA-MCS defines the required control. The Assessment and Evidence Guide tests whether it operates. JA-ES structures and verifies the evidence. Guard evaluates the system and the population.
