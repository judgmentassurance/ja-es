# Changelog — Judgment Assurance Evidence Schema (JA-ES)

Published version paths are never overwritten.

## v0.6 packaging correction — no schema change

- `verify.py` skips non-record JSON metadata such as array-valued manifests
  instead of passing it to object-oriented validation.
- A suite directory containing independent scenario subdirectories is verified
  scenario by scenario. `verify.py test-action-verification/` now runs and
  rejects all three adversarial action cases.
- A run that finds no Evidence Records or Linked Events fails explicitly;
  verification can no longer pass after reading nothing.
- The standalone reference demo contains no external script or stylesheet
  requests. The JA-ES v0.6 schemas, examples and record hashes are unchanged.
- The README contents and verification path now surface the separate
  `guard-prototype/`, while preserving the category boundary: it is a
  population-level Guard assurance artifact, not a fourth JA-ES record type.

## v0.6 — action authorization and execution evidence

Substantive record-format release. v0.5 could prove that a case satisfied the
eligibility conditions for automation, but it did not state in structured form
which outcomes the boundary authorized or what action the system actually made
operative. It therefore risked conflating an AI recommendation, authority to
act, and execution.

### Added — governed action scope
- Governance `boundary_scope` now requires `permitted_automated_actions` and
  `prohibited_automated_actions`. A boundary answers both when automation may
  act and what it may do.
- Lending examples authorize automatic `approve` only. `deny`, `modify_terms`
  and `change_pricing` route to a human or another governed process.

### Added — recommendation versus execution
- `ai_output.recommended_action` is required on `auto_execution_log`.
- New required `automated_execution` object records `executed_action` and a
  plain-language `execution_summary` separately from the AI output.
- Condition results include `AUTO-ACTION-PERMITTED`, binding the observed
  action to the permitted action set used by the rule engine.

### Added — cross-record action verification
- `verify.py` resolves the governance record and confirms that the executed
  action is permitted, is not prohibited, matches the recommendation, and is
  represented by exactly one action-permission condition whose threshold
  matches the sealed boundary.
- Three schema-valid, hash-valid and chain-valid adversarial scenarios cover an
  unpermitted automated denial, recommendation/execution mismatch, and
  substitution of the permitted action set.
- `test-invalid/` 41 → 44 for missing recommendation, missing executed action,
  and automated-execution claims on human records.

### Recomputed
- All eight examples, linked events, chains and the end-to-end record-hash test
  vector were rebuilt under `JA-ES-0.6` / `JA-ES-LE-0.6`.

## v0.5.2 — test vector hardening

No schema changes to JA-ES records. Adds discriminating canonicalization
vectors and corrects two that were weaker than described.

- **`utf16-vs-codepoint-ordering`** (new). The prior Unicode vector used only
  BMP characters, so code-point ordering and UTF-16 code-unit ordering give the
  same answer and the vector could not tell them apart. The new vector pairs
  U+1D400 (supplementary, encoded as surrogate pair D835 DC00) against U+FFFD:
  UTF-16 sorts the supplementary character FIRST, code-point ordering sorts it
  LAST. RFC 8785 requires UTF-16. A plausible BMP-only implementation passes
  every other vector and fails this one.
- **`negative-zero`** (new). The prior vector contained ordinary integer 0, not
  IEEE-754 -0.0, so it never exercised the rule. -0.0 canonicalizes to 0.
- **`number-formatting`** expanded to the ECMAScript Number::toString boundaries
  that actually diverge: 1e21 and 1e20, 1e-7 and 1e-6, max safe integer,
  denormal minimum, and double maximum.
- **`string-escaping-controls`** (new): control characters below U+0020, short
  escapes, and confirmation that printable non-ASCII is not escaped.

Nine vectors. `verify.py --self-test`.

## v0.5.1 — corrections and test vectors

No schema changes. Corrects two overstated claims in the v0.5 prose.

- **The under-routing claim was too strong.** `boundary_evaluation` explains
  routing for cases that were recorded and supplies the per-case detail a
  reconciliation control needs. It does not itself make under-routing
  detectable: a decision never recorded leaves no evidence of its own absence.
- **The chaining claim was too broad.** Within the set presented, chaining
  reveals alteration, substitution and interior deletion. It does not establish
  that every required record was created, that the population is complete, or
  that the chain was not truncated — tail removal leaves no gap. An unsigned
  chain does not resist wholesale regeneration.
- Non-creation, population completeness, truncation and regeneration added to
  "what the schema cannot enforce".
- `test-vectors.json` and `verify.py --self-test` added.

## v0.5 — draft for review

Additive release. No breaking changes to v0.4 records; every v0.4 record remains
valid under v0.5 after a version-string bump.

Surfaced by building a working interactive implementation. The demo let a user
set a score below the auto-approval floor and correctly reported that the
decision "must route to a human Judgment Record instead" — and then there was
nowhere in the schema to record that. That path had no evidentiary home.

### Added — `boundary_evaluation` on judgment records
- New optional object on `judgment_record`: evidence that a decision was
  machine-evaluated against an automation boundary, **failed**, and was
  therefore routed to a human. The inverse of `authorizing_boundary`.
- Carries the governance record id **and hash** of the boundary evaluated, the
  versioned rule set, per-condition results, and `scored_at` /`evaluated_at` /
  `routed_to_human_at`.
- Why it matters: v0.4 could prove auto-executed decisions stayed inside the
  boundary, but could not prove escalated decisions fell outside it. That left
  **under-routing undetectable** — an organization auto-executing what should
  have escalated leaves normal-looking judgment records that say nothing about
  what was never routed — and deprived Guard of per-condition escalation signal.

### Added — polarity enforcement in both directions
- `boundary_evaluation.all_conditions_passed` must be `false` **and**
  `condition_results` must contain at least one failed condition. A decision
  satisfying every condition would have auto-executed and cannot be a judgment
  record.
- `authorizing_boundary.condition_results` must now report `passed: true` on
  **every** condition, not merely a true summary flag. A decision failing any
  condition cannot be an auto-execution.
- Record types now mutually exclude the wrong evaluation object: judgment
  records cannot claim authority, auto-executions cannot claim failed
  evaluation, governance records can carry neither.

### Changed
- `condition_results` extracted to `$defs/conditionResults` and shared by both
  evaluation objects, so the two directions cannot drift apart.
- `verify.py` now resolves `boundary_evaluation` links against sealed boundary
  hashes, alongside authority and lineage.

### Added — examples and tests
- Eighth example: an application scoring 739 — one point under the new floor —
  that the machine refused to auto-execute and routed to an analyst, who
  reviewed the full file and approved it. It records precisely which condition
  failed, and notes that under boundary v1.3 the same application would have
  auto-executed.
- `test-invalid/` 34 → 41 cases, the seven new ones covering polarity in both
  directions and hash-binding of the evaluated boundary.
- `test-integrity/` 6 → 7: an observed value edited after sealing to make a
  routed decision look like a near-pass.

## v0.4 — superseded

Conformance, verification and packaging release. v0.3 was conceptually right
but not actually verifiable.

### Fixed — the examples were not verifiable
- **All example hashes were decorative.** v0.3 specified RFC 8785 + SHA-256 and
  then carried invented hex strings. Every example is now built by
  `build_examples.py`, which computes real hashes in chain order. `verify.py`
  confirms them.
- **Chain scoping was internally contradictory.** v0.3 claimed sequences were
  gapless within an Envelope while placing a governance record at sequence 41
  and a judgment record at 44127 in the same Envelope. Added required
  `integrity.chain_id`; sequence is gapless within a chain, and governance and
  operational records occupy separate chains.
- **The governance example was retroactive.** Its boundary took effect at
  00:00Z while the approver decided at 15:40Z, purporting to authorize sixteen
  hours of earlier decisions. Corrected, and `retroactive_authorization` added
  as an explicit declared flag requiring justification, since JSON Schema cannot
  compare two field values.

### Added — authority and traceability
- `authorizing_boundary.condition_results`: per-condition evaluation against a
  versioned rule set (rule id, operator, threshold, observed value, pass/fail).
  Citing a boundary showed which authority was claimed; this shows the decision
  actually fell inside it. `all_conditions_passed` must be true.
- `boundary_scope.rule_set_id` / `rule_set_version` — required.
- `authorizing_boundary.scored_at` / `boundary_evaluated_at` / `executed_at` —
  required, making cutover behaviour auditable.
- `governance_action.transition_policy`: cutover method, in-flight treatment,
  optional score validity window, and grandfathering (which requires an express
  population, deadline and rationale). Default rule: the boundary in force when
  a decision becomes operative governs it.
- `governance_action.supersedes_record_hash` — lineage now binds by hash, not
  id alone, closing the same substitution gap already closed for authority.
- `suspend` and `withdraw` now require predecessor id and hash, alongside
  `modify`, `reaffirm` and `narrow`.
- Auto-execution now requires `envelope.trigger` with `escalated: false`, a rule
  id, and an automation-appropriate basis.
- Linked events now enforce exactly one payload matching the declared
  `event_type` (an outcome event could previously also carry an amendment).

### Added — verification, which schema validation cannot do
- `verify.py`: checks schema, recomputes every hash, walks each chain for gaps
  and broken links, and resolves cross-record references (authority, lineage,
  linked events) against sealed hashes.
- `build_examples.py`: reference implementation of the hashing and chaining
  rules, so they are unambiguous rather than described.
- `test-integrity/`: six records that are **schema-valid** and fail
  verification — altered rationale, swapped attribution, repointed authority,
  repointed lineage, sequence gap, broken chain link. These exist to make the
  limit of schema validation concrete.
- `test-invalid/` expanded from 21 to 34 cases covering the new constraints.
- Seventh example: the original boundary the narrowing supersedes, so lineage
  can be verified end to end rather than asserted.

### Fixed — packaging and documentation
- LICENSE attribution string read "Judgment Assurance Judgment Assurance
  Evidence Schema". Corrected.
- README now documents Ajv strict-mode behaviour rather than claiming any
  validator works unmodified.
- Directory structure documented explicitly (`examples/`, `test-invalid/`,
  `test-integrity/` are directories, not flattened files).

## v0.3 — superseded
Renamed JA-JRS → JA-ES. Added `governance_judgment_record` and required
`authorizing_boundary` on auto-execution logs. Separate governance reasoning
vocabulary. Boundary lineage by id.

## v0.2 — superseded
Corrective release: `human_action` wrongly required at top level; permitted
empty; post-decision data written into sealed records; hash coverage excluding
chain-critical fields; optional sequence and prior hash; no canonicalization;
probe requirements in prose only. Renamed `action` → `ai_output_disposition`.

## v0.1 — unpublished
Initial draft. Do not implement.
