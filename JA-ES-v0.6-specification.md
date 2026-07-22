# Judgment Assurance Evidence Schema (JA-ES) v0.6

**Open specification for decision evidence under the Judgment Assurance framework.**

Draft for review. Not yet validated against a live implementation.

---

## Terminology

The framework distinguishes the control activity from the evidence it produces. The schema follows that distinction exactly.

**Atomic Unit** — the control event: the actual exercise of governed human judgment (Define, Decide, Record, Own) at a point of decision. An activity, occurring in time.

**Judgment Record** — the durable evidentiary artifact produced by a completed Atomic Unit. A document.

*An Atomic Unit produces a Judgment Record.* The analyst reviewing and rejecting an AI lending recommendation is the Atomic Unit; the resulting structured record is the Judgment Record. Calling the record an "Atomic Unit" would blur the control with its evidence.

**Auto-Execution Log** — evidence of a decision resolved inside an approved reliance boundary without contemporaneous human review. It is *not* the product of a contemporaneous Atomic Unit, and this schema does not pretend otherwise.

The umbrella term is **Evidence Record**, covering all three record types below. Hence JA-ES rather than a schema named only for Judgment Records.

---

## The three record types, and why there are three

**`judgment_record`** — an Atomic Unit at the point of an individual decision. A human saw an AI output and accepted, modified, rejected, escalated, or deferred it, with structured reasoning and named ownership.

**`governance_judgment_record`** — an Atomic Unit at the Governance layer. Someone decided that a defined population of decisions may proceed *without* contemporaneous human review, and recorded why, under what conditions, with what evidence, effective when, and reviewable when.

**`auto_execution_log`** — a decision that executed inside such a boundary, linked by id **and hash** to the governance judgment that authorized it, with the recommended action and action actually executed stated separately.

A judgment record may additionally carry **`boundary_evaluation`**: evidence that the decision was machine-evaluated against an automation boundary, *failed*, and was therefore routed to a human. It is the inverse of `authorizing_boundary` and uses the same per-condition structure.

The third type exists because of a gap the framework already anticipated but the schema previously left implicit. The whitepaper states that the choice to exempt a category of decisions from human review "is itself a judgment decision. It must be documented, justified, and owned." If that is true — and it is the correct position — then the boundary approval is an Atomic Unit, and it produces a Judgment Record like any other. Its subject is a threshold rather than a case, and it sits at the Governance layer rather than the operational one, but structurally it is the same thing.

That yields the model:

**Governance Atomic Unit → Governance Judgment Record → N Auto-Execution Logs, each pointing back to it.**

Every auto-executed decision is therefore traceable to a specific, dated, owned, versioned exercise of human judgment. Not a contemporaneous one — that distinction is preserved and is the whole reason for a separate record type — but never an absent one.

This is a materially stronger evidentiary position than "auto-execution is governed by policy." Asked why forty thousand loans had no human in the loop, the answer is not a policy document. It is: here is the named individual who decided that, here is the date, here is their structured reasoning, here is the evidence they relied upon, here is the version in force at the time of each of those decisions, and here is the prior boundary it superseded.

**`authorizing_boundary` binds by hash, not just by id.** A version string can be reassigned; a hash cannot. Hash-binding means an auto-execution record cannot be quietly re-pointed at a rewritten boundary, and it detects substitution of the authorizing judgment after the fact.

---

## The two-file model

**`evidence-record.schema.json`** — the immutable record, written once, at the decision point.

**`linked-event.schema.json`** — everything learned afterwards: realized outcomes, corrections, probe evaluations. Each references the original by id and hash.

This split is not tidiness. An Evidence Record's value rests on being contemporaneous and tamper-evident. Appending post-decision information to the original would alter its hashed content — precisely what the tamper-evidence claim says cannot happen. It also has an evidentiary benefit: the record carries no post-hoc grade, so what the decision-maker knew and reasoned at the moment stays uncontaminated by what was learned later.

---

## Design decisions worth knowing about

**Two reasoning vocabularies, not one.** Case-level Tier A asks *why this decision*; governance Tier A asks *why may this population proceed without a human*. These are different questions and share almost no vocabulary — "contradictory evidence" is meaningless for a boundary approval, and "reversibility of decision" is meaningless for a single case. Forcing one enum to serve both would have produced reasoning codes that fit neither. Tier B remains organization-defined and version-stamped in both.

**Boundary lineage is enforced.** A `modify`, `reaffirm`, or `narrow` disposition requires `supersedes_record_id`. Boundaries drift by accretion; requiring each version to name its predecessor makes the drift a traceable chain rather than a series of unconnected approvals.

**`ai_output_disposition`, not `action`.** Records what the human did *to the AI output*, not the outcome for the subject. A disposition of `reject` on an AI decline may produce an approval. Conflating them is how oversight statistics get misread; `final_outcome` carries the plain-language result.

**Reasoning is a required object, not a string.** Free text cannot satisfy it, encoding JA-MCS §6. Tier A enums are closed to preserve cross-organization comparability; Tier B is the extensible layer.

**`time_on_decision_ms`.** Optional but load-bearing: the cleanest quantitative signal for reasoning present in form but perfunctory in substance. Structured reasoning selected in two seconds, at volume, is the pattern-level signal of systemic control failure.

**`presented_to_human` is recorded, not inferred.** Makes blind decision events and auto-executions distinguishable in the data. It is what makes anchoring analysis possible.

**Reconstruction is flagged, never silent.** `reconstructed: true` forces `contemporaneous: false` and requires a basis.

**Hash chaining, specified precisely.** Hash input is the RFC 8785 (JCS) serialization of the record with `record_hash` and `signature` removed from the integrity object — so `chain_id`, `sequence` and `prev_record_hash` are themselves covered. Without a fixed canonicalization, two conformant implementations would compute different hashes over the same record; `test-vectors.json` and `verify.py --self-test` exist so that agreement can be demonstrated rather than assumed.

**What chaining does and does not establish.** Within the record set presented, chaining reveals *alteration* (hash mismatch), *substitution* (a repointed reference), and *interior deletion* (sequence gap and broken linkage). It does not establish that every required record was created, that the presented population is complete, or that the chain was not **truncated** — removing records from the tail produces no gap and no broken link. Nor does an unsigned chain resist wholesale **regeneration**: an actor able to rewrite the entire set can recompute every hash consistently. Closing those requires something outside the record set — signatures over chain heads, an externally anchored or independently held checkpoint, and reconciliation against a population the recording process does not control.

**Chains are explicitly scoped, not implied by Envelope.** `sequence` is gapless within a `chain_id`, not across an Envelope. Governance records and operational decision records occupy separate chains — their volumes differ by three or four orders of magnitude, and interleaving a handful of boundary approvals into a stream of forty thousand auto-executions would make gap detection meaningless. Convention: `<envelope_id>/governance` and `<envelope_id>/decisions`.

**Auto-execution proves satisfaction, not just citation.** `authorizing_boundary.condition_results` reports every rule in the boundary's versioned rule set with operator, threshold, observed value and pass/fail. Citing a boundary shows which authority was claimed; per-condition results show the decision actually fell inside it. Every condition must be reported, including those that passed trivially — a partial report is indistinguishable from a suppressed failure.

**Eligibility and action authorization are separate.** A boundary must answer both *when may the machine act?* and *what may it do?* `boundary_scope.permitted_automated_actions` and `prohibited_automated_actions` state the authorized outcome set in structured form. An approval-only lending boundary does not silently become authority to deny because a score condition passed. Every Auto-Execution Log records `ai_output.recommended_action` separately from `automated_execution.executed_action`, and includes an `AUTO-ACTION-PERMITTED` condition result. Verification confirms that the recommendation and execution match, that the executed action is permitted and not prohibited, and that the condition's permitted set matches the sealed governance record. A recommendation is not evidence of execution; an execution timestamp is not evidence of what occurred.

**Routing is evidenced in both directions.** `boundary_evaluation` records why a decision that reached a human went there: which boundary was evaluated, which conditions failed, bound by hash to the boundary version in force. Without it, an organization can show that auto-executed decisions satisfied the boundary but can offer nothing about *why* anything else escalated, and Guard loses per-condition signal — "escalations rose 12% this quarter" is far less actionable than "escalations from `AUTO-SCORE-FLOOR` rose 12% while every other condition held flat."

Note carefully what this does **not** establish. `boundary_evaluation` explains routing *for cases that were recorded*, and it supplies the per-case detail a reconciliation control needs. It does not by itself make under-routing detectable. A decision that was never recorded leaves no evidence of its own absence, and every surviving record can be individually true while the population is materially incomplete. Detecting omitted, duplicated, or substituted cases requires reconciling the presented records against an independently sourced population — a Guard-layer control operating over a set, not a property of any individual record. See "what the schema cannot enforce."

The polarity is enforced in both directions: a judgment record's evaluation must report `all_conditions_passed: false` **and** contain at least one failed condition, while an auto-execution record's conditions must every one report `passed: true`. A decision satisfying every condition would have auto-executed and cannot be a judgment record; a decision failing any condition cannot be an auto-execution.

**Boundary transitions have a default rule.** The boundary in force when a decision becomes *operative* governs it. Scoring under an earlier boundary does not vest authority to execute under that boundary after it has been superseded. Decisions already executed under v1.3 remain tied to v1.3; decisions scored under v1.3 but not yet executed when v1.4 takes effect are re-evaluated under v1.4, or escalate if they cannot be. Grandfathering is permitted only where the new governance judgment expressly defines a transition population, deadline and rationale. `transition_policy` records the choice; `scored_at` / `boundary_evaluated_at` / `executed_at` on each auto-execution log make it auditable. A `score_validity_window_hours` guards the specific abuse this prevents: batch-scoring a large population immediately before a narrowing and continuing to execute it afterwards under superseded authority.

**Retroactive authorization is declared, not inferred.** JSON Schema cannot compare two field values, so it cannot detect that `effective_from` precedes `decision_at`. `retroactive_authorization` is an assertion the issuer makes and an assessor tests, and it requires justification. A boundary that silently backdates its own effect is one of the more serious things an assessor could find, and the schema at least forces the question to be answered explicitly.

---

## What the schema enforces, and what it cannot

State this to any assessor, underwriter, or regulator relying on machine validation.

**Machine-enforced — a validator answers definitively:**

- Attribution present on every record
- Structured reasoning present and not free-text-only
- Tier B codes version-stamped; governance records use governance reasoning vocabulary
- Record linked to an Envelope and reliance standard version
- **Every auto-executed decision linked by id and hash to the governance judgment that authorized it**
- **Every auto-executed decision reports per-condition results against a versioned rule set, all passing**
- **Every governance boundary states permitted and prohibited automated actions in structured form**
- **Every Auto-Execution Log separately records the recommended action and the action actually executed**
- **Decisions routed to a human by a failed boundary evaluation report which conditions failed, bound by hash to the boundary evaluated**
- Record-type polarity: a passed evaluation cannot appear on a judgment record, a failed condition cannot appear on an auto-execution
- Boundary changes, suspensions and withdrawals identify the predecessor by id **and hash**
- Retroactive authorization carries a justification; grandfathering carries a population, deadline and rationale
- Auto-execution records the routing trigger and is not marked escalated
- Linked events carry exactly one payload, matching their declared type
- `modify` carries detail; `escalate` carries a target
- Record-type separation: no case action on governance records, no human action on auto-execution, correct owner type for each
- Reconstructed records flagged and unable to claim contemporaneity
- Chain structurally intact: sequence present, prior hash present, canonicalization declared
- Probes assert sandboxing and record ground-truth provenance and owner
- No unrecognized or misspelled fields anywhere

**Verifier-enforced across records — schema validation alone cannot establish:**

- The executed action is included in the referenced governance record's sealed permitted-action set
- The executed action is not expressly prohibited by that boundary
- The AI's recommended action matches the action actually executed
- The `AUTO-ACTION-PERMITTED` condition reports the executed action and the same permitted set sealed in the boundary

**Not machine-enforceable — requires human assessment; no validator result covers these:**

- **Whether the reasoning is *sufficient*.** The Sufficiency Test (Assessment Guide §7.5, §8) asks whether reasoning addresses the decision context and explains the basis for the action. A record can be perfectly conformant and materially insufficient. This is the single most important limit.
- **Whether a boundary is *appropriate*.** A governance record can be flawlessly structured and authorize far too much. The schema records the judgment; it cannot evaluate it.
- **Whether the probe was actually sandboxed.** The schema enforces the assertion, not the fact.
- **Whether ground truth is genuinely independent** of the reviewers being tested. Provenance is recorded so an assessor can evaluate it; the schema cannot.
- **Whether the record is truthful.** A fabricated but well-formed record validates.
- **Whether every required record was created.** This is the largest gap and the least intuitive. Absence leaves no trace: a decision silently auto-executed that should have routed, or dropped entirely, produces a chain that verifies perfectly around the hole. Every record present is true; the population is a lie.
- **Whether the presented population is complete, or the chain untruncated.** Records removed from the tail leave no sequence gap. Counts alone do not close this either — `100 evaluated = 90 auto + 10 routed` balances just as neatly with duplicates, substituted cases, or the wrong ten referrals. A defensible control reconciles identities or deterministic set digests against an independently sourced population, not totals.
- **Whether the chain was wholesale regenerated.** Without signatures over chain heads or an externally held checkpoint, an actor with full write access can rebuild a consistent chain.
- **Whether the in-scope population is correctly defined.** An organization can conformantly record a trivial slice of its consequential decisions.
- **Whether Guard acted** on what it found.
- **Whether hashes are cryptographically valid, or whether a record was altered after sealing.** This is the most important gap in practice. A record whose rationale was rewritten last week is *schema-valid*: the fields are present and well-formed. Only recomputation catches it. `test-integrity/` contains six such records and `verify.py` performs the check. Never treat a green schema result as verification.
- **Whether `effective_from` precedes `decision_at`.** JSON Schema cannot compare two values in the same document. Hence the declared `retroactive_authorization` flag.

Machine validation establishes that the *form* of governance is present. It says nothing about whether judgment was sound. That is not a defect of the schema — it is the framework's own acknowledged boundary, expressed in software.

---

## Open questions for pilot validation

Treat the schema as a hypothesis. The first pilots exist partly to break it.

1. **Are the two Tier A enums right?** Both are guesses. Watch for codes never selected and narratives repeatedly expressing something no code covers.
2. **Does `narrative` carry disproportionate signal?** If most records lean on free text, the structured tiers are mis-scoped.
3. **Is `subject_ref` pseudonymization workable** where the decision record and case record are the same object?
4. **What permitted window can decision-makers actually meet** under production pressure, by risk tier?
5. **Does `time_on_decision_ms` survive** works-council, union, or privacy review? Best perfunctory-review signal, most surveillance-adjacent field.
6. **Does auto-execution log volume overwhelm storage** at real transaction rates, and does that pressure organizations toward under-scoping the Envelope?
7. **Does the linked-event model hold** when outcomes arrive years later and referenced records have been archived to cold storage? Linked events bind by hash, so archival must not re-serialize originals.
8. **Does the default cutover rule survive contact with operations?** The rule — boundary in force at execution governs, in-flight decisions re-evaluate — is correct in principle. What pilots must establish is whether re-evaluation is technically possible in the transaction system, and what the escalation volume looks like on a cutover day.
9. **Is per-condition reporting affordable** at forty thousand decisions a year, or does the volume push organizations toward coarser rule sets that report less?
10. **Is `boundary_evaluation` capturable** where routing happens in a transaction system that discards the evaluation result once it has routed? This is the most likely place a real implementation will push back, and the answer determines whether under-routing is detectable in practice or only in principle.

Do not freeze the schema until a real workflow has run against it. Treat schema stability — not integration completeness — as the signal that it is time to build connectors.

---

## Implementation note

Nothing here requires a platform. A conformant capture layer is: a form that emits this structure, an identity and timestamp binding, an append-only store with hash chaining, and an embed or webhook into whatever system the decision already lives in. Forms are appropriate technology for pilots one through three, because the schema is still learning.

Note that governance judgment records are low-volume and high-value. An organization can produce conformant governance records with no engineering at all — they are written a handful of times a year, by hand, by the person who owns the boundary. That is a realistic first artifact for any pilot, and it is the record most likely to matter in litigation.

---

*Judgment Assurance (Kavalir, 2026). Field derivations traced to JA-MCS v1.0, JA Architecture v1.1, JA Assessment & Evidence Guide v1.0, JAMM-PS v0.1, and JA-UQ v1.1.*
