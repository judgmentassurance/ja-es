#!/usr/bin/env python3
"""
JA-ES reference implementation — hash computation and chain construction.

Canonical hash rule:
    input  = the entire record, with 'record_hash' and 'signature' removed
             from the integrity object
    encode = RFC 8785 JSON Canonicalization Scheme
    digest = SHA-256, lowercase hex

Chain rule:
    sequence is monotonic and gapless within a chain_id (NOT across an Envelope)
    prev_record_hash is required except where chain_genesis is true

Requires: pip install rfc8785
"""
import json, hashlib, copy, os
import rfc8785

HASH_EXCLUDED = ("record_hash", "signature")


def compute_record_hash(record: dict) -> str:
    """Canonical JA-ES record hash."""
    c = copy.deepcopy(record)
    c["integrity"] = {k: v for k, v in c["integrity"].items() if k not in HASH_EXCLUDED}
    return hashlib.sha256(rfc8785.dumps(c)).hexdigest()


def seal(record: dict, chain_id: str, sequence: int, prev_hash: str | None) -> str:
    """Populate integrity fields and return the record hash."""
    integ = record.setdefault("integrity", {})
    integ["chain_id"] = chain_id
    integ["sequence"] = sequence
    integ["hash_algorithm"] = "SHA-256"
    integ["canonicalization"] = "RFC8785"
    if prev_hash is None:
        integ["chain_genesis"] = True
        integ.pop("prev_record_hash", None)
    else:
        integ["chain_genesis"] = False
        integ["prev_record_hash"] = prev_hash
    integ.pop("record_hash", None)
    h = compute_record_hash(record)
    integ["record_hash"] = h
    return h


def verify_record(record: dict) -> bool:
    return record["integrity"]["record_hash"] == compute_record_hash(record)


def verify_chain(records: list[dict]) -> list[str]:
    """Returns a list of problems; empty list means the chain verifies."""
    problems = []
    ordered = sorted(records, key=lambda r: r["integrity"]["sequence"])
    prev = None
    expected_seq = 1
    for r in ordered:
        rid, integ = r["record_id"], r["integrity"]
        if not verify_record(r):
            problems.append(f"{rid}: record_hash does not match recomputed hash (altered)")
        if integ["sequence"] != expected_seq:
            problems.append(f"{rid}: sequence {integ['sequence']}, expected {expected_seq} (deletion)")
        if prev is None:
            if not integ.get("chain_genesis"):
                problems.append(f"{rid}: first record in chain but chain_genesis is not true")
        else:
            if integ.get("prev_record_hash") != prev:
                problems.append(f"{rid}: prev_record_hash does not match prior record (chain break)")
        prev = integ["record_hash"]
        expected_seq = integ["sequence"] + 1
    return problems


# --------------------------------------------------------------------------
# Example construction
# --------------------------------------------------------------------------

GOV_CHAIN = "ENV-CONSUMER-LENDING/governance"
DEC_CHAIN = "ENV-CONSUMER-LENDING/decisions"
HR_CHAIN = "ENV-CONDUCT-ALERTS/decisions"


def gov_v13():
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "GJR-LEND-2025-0401-000004",
        "record_type": "governance_judgment_record",
        "envelope": {
            "envelope_id": "ENV-CONSUMER-LENDING", "envelope_version": "2.2",
            "workflow": "Consumer Loan Origination",
            "reliance_standard_id": "RS-AUTO-APPROVE", "reliance_standard_version": "1.3"
        },
        "decision": {
            "decision_type": "reliance_boundary_approval", "decision_domain": "lending",
            "risk_tier": "moderate", "impact_categories": ["financial", "rights", "compliance"]
        },
        "boundary_scope": {
            "ai_system_ids": ["CREDIT-SCORE-ENGINE-2"],
            "decision_population": "Consumer instalment loan applications, requested amount at or below $10,000, composite risk score at or above 720, no adverse action indicators.",
            "rule_set_id": "RULES-AUTO-APPROVE-BAND-A", "rule_set_version": "1.3",
            "auto_execution_conditions": "Approval may execute without contemporaneous human review where all Band A conditions are satisfied at time of scoring. Any unmet condition routes to human review. All declines escalate.",
            "permitted_automated_actions": ["approve"],
            "prohibited_automated_actions": ["deny", "modify_terms", "change_pricing"],
            "excluded_conditions": "All declines; fraud flag; thin-file indicator; prior adverse action within 24 months; manual referral.",
            "estimated_annual_volume": 47000,
            "review_cadence": "Quarterly, and immediately upon material model change or adverse outcome signal.",
            "next_review_due": "2025-07-01", "sampling_rate": 0.02
        },
        "governance_action": {
            "boundary_disposition": "approve",
            "effective_from": "2025-04-07T00:00:00Z",
            "approving_body": "AI Governance Committee",
            "dissent_recorded": "None recorded.",
            "retroactive_authorization": False,
            "transition_policy": {"cutover_method": "scheduled", "in_flight_treatment": "re_evaluate_under_new_boundary", "score_validity_window_hours": 72},
            "reasoning": {
                "tier_a": ["model_performance_evidence", "within_stated_risk_appetite", "reversibility_of_decision", "volume_or_capacity_justification"],
                "tier_b": [{"code": "BAND-A-ESTABLISH", "label": "Initial establishment of Band A auto-approval", "library_version": "2.2"}],
                "narrative": "Establishes automated approval for Band A. Model validation for CSE-2 v4.1 shows stable rank-ordering across the 700+ range on a 24-month backtest. Score floor set at 720 with a $10,000 ceiling. Declines are excluded entirely from automation given adverse-action obligations. Decisions remain reversible prior to funding. Quarterly review required; boundary to be revisited on first full cohort performance data.",
                "standard_applied": "Credit Policy 4.0 — Automated Decisioning Authority",
                "evidence_relied_upon": ["Model Validation Report CSE-2 v4.1 (Model Risk Management, 2025-03-12)", "Backtest Analysis 2023-2025 (Credit Risk Analytics, 2025-03-20)"]
            }
        },
        "ownership": {"owner_type": "governance_authority", "owner_id": "EMP-30055",
                      "role_at_decision": "VP Consumer Credit — Accountable Owner, ENV-CONSUMER-LENDING",
                      "override_authority": True},
        "timing": {"decision_at": "2025-04-01T14:10:00Z", "recorded_at": "2025-04-01T14:35:00Z",
                   "permitted_window_minutes": 1440, "contemporaneous": True, "reconstructed": False},
        "integrity": {},
        "retention": {"retain_until": "2035-04-01", "retention_basis": "Governance record retained for life of boundary plus 10 years"}
    }


def gov_v14(prev_gov_hash):
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "GJR-LEND-2026-0102-000007",
        "record_type": "governance_judgment_record",
        "envelope": {
            "envelope_id": "ENV-CONSUMER-LENDING", "envelope_version": "2.3",
            "workflow": "Consumer Loan Origination",
            "reliance_standard_id": "RS-AUTO-APPROVE", "reliance_standard_version": "1.4"
        },
        "decision": {
            "decision_type": "reliance_boundary_approval", "decision_domain": "lending",
            "risk_tier": "moderate", "impact_categories": ["financial", "rights", "compliance"]
        },
        "boundary_scope": {
            "ai_system_ids": ["CREDIT-SCORE-ENGINE-2"],
            "decision_population": "Consumer instalment loan applications, requested amount at or below $10,000, composite risk score at or above 740, no adverse action indicators, applicant not in a protected-review category.",
            "rule_set_id": "RULES-AUTO-APPROVE-BAND-A", "rule_set_version": "1.4",
            "auto_execution_conditions": "Approval may execute without contemporaneous human review where all Band A conditions are satisfied simultaneously at time of scoring. Any single condition unmet routes to human review. All declines escalate regardless of score.",
            "permitted_automated_actions": ["approve"],
            "prohibited_automated_actions": ["deny", "modify_terms", "change_pricing"],
            "excluded_conditions": "All declines; any file with a fraud flag, thin-file indicator, prior adverse action within 24 months, or manual referral from underwriting.",
            "estimated_annual_volume": 41000,
            "review_cadence": "Quarterly, and immediately upon material model change or adverse outcome signal.",
            "next_review_due": "2026-04-05", "sampling_rate": 0.02
        },
        "governance_action": {
            "boundary_disposition": "narrow",
            "effective_from": "2026-01-05T00:00:00Z",
            "supersedes_record_id": "GJR-LEND-2025-0401-000004",
            "supersedes_record_hash": prev_gov_hash,
            "approving_body": "AI Governance Committee",
            "dissent_recorded": "None recorded.",
            "retroactive_authorization": False,
            "transition_policy": {
                "cutover_method": "scheduled",
                "in_flight_treatment": "re_evaluate_under_new_boundary",
                "score_validity_window_hours": 72
            },
            "reasoning": {
                "tier_a": ["prior_boundary_performance", "historical_outcome_review", "within_stated_risk_appetite", "reversibility_of_decision"],
                "tier_b": [{"code": "BAND-A-RAISE-FLOOR", "label": "Auto-approval score floor raised following cohort performance review", "library_version": "2.3"}],
                "narrative": "Prior boundary (v1.3) set the auto-approval floor at 720. Twelve-month cohort review of 38,412 auto-approved originations shows 90+ day delinquency of 1.9% in the 720-739 band versus 0.7% at 740+. Raising the floor to 740 moves roughly 6,800 applications per year into human review, which capacity modelling confirms underwriting can absorb at current headcount. Decisions remain reversible prior to funding. Declines continue to escalate without exception. Boundary narrowed rather than withdrawn because performance at 740+ remains within stated appetite. Effective date set three days after approval to allow rule-set deployment; in-flight applications scored under v1.3 re-evaluate under v1.4, with a 72-hour score validity window to prevent pre-narrowing batch scoring being executed under superseded authority.",
                "standard_applied": "Credit Policy 4.0 — Automated Decisioning Authority; Enterprise Risk Appetite Statement §3.2",
                "evidence_relied_upon": [
                    "Cohort Performance Review 2025-Q4 (Credit Risk Analytics, 2025-12-08)",
                    "Model Validation Report CSE-2 v4.2.1 (Model Risk Management, 2025-11-19)",
                    "Underwriting Capacity Assessment 2026 (Operations, 2025-12-15)"
                ]
            }
        },
        "ownership": {"owner_type": "governance_authority", "owner_id": "EMP-30055",
                      "role_at_decision": "VP Consumer Credit — Accountable Owner, ENV-CONSUMER-LENDING",
                      "override_authority": True},
        "timing": {"decision_at": "2026-01-02T15:40:00Z", "recorded_at": "2026-01-02T15:52:00Z",
                   "permitted_window_minutes": 1440, "contemporaneous": True, "reconstructed": False},
        "integrity": {},
        "retention": {"retain_until": "2036-01-02", "retention_basis": "Governance record retained for life of boundary plus 10 years"}
    }


def lending_jr():
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "JR-LEND-2026-0716-004412",
        "record_type": "judgment_record",
        "envelope": {
            "envelope_id": "ENV-CONSUMER-LENDING", "envelope_version": "2.3",
            "workflow": "Consumer Loan Origination — Decline Review",
            "reliance_standard_id": "RS-CREDIT-DECLINE", "reliance_standard_version": "1.4",
            "trigger": {"escalated": True, "trigger_rule_id": "TR-DECLINE-ALL", "trigger_basis": "exception_rule"}
        },
        "decision": {"decision_type": "credit_decline_review", "decision_domain": "lending", "risk_tier": "high",
                     "subject_ref": "APP-2026-884213", "impact_categories": ["financial", "rights", "compliance"]},
        "ai_output": {
            "system_id": "CREDIT-SCORE-ENGINE-2", "vendor": "Internal", "model_version": "4.2.1",
            "output_type": "recommendation",
            "recommended_action": "deny",
            "output_summary": "Decline. Composite risk score 612, below origination floor of 640. Primary drivers: DTI 47%, two 30-day delinquencies in trailing 24 months.",
            "output_value": 612, "confidence_reported": 0.86, "presented_to_human": True
        },
        "human_action": {
            "ai_output_disposition": "reject",
            "final_outcome": "Loan APPROVED at reduced line of $8,000, 24-month term. AI decline recommendation not followed.",
            "reasoning": {
                "tier_a": ["contextual_factors_not_visible_to_system", "contradictory_evidence"],
                "tier_b": [
                    {"code": "DTI-DOC-CORRECTION", "label": "Verified income documentation materially changes DTI from application value", "library_version": "2.3"},
                    {"code": "DELINQ-ISOLATED-CAUSE", "label": "Delinquencies attributable to documented isolated event, not payment pattern", "library_version": "2.3"}
                ],
                "narrative": "Applicant submitted 2025 W-2 and two most recent pay stubs after initial pull; verified gross income is $71,400 vs. $58,000 stated at application, moving DTI to 38%. Both 30-day delinquencies fall in a single 3-month window in Q1 2025 coinciding with documented medical leave; 21 months of on-time payments since. Score floor not met on stale income data. Approving at reduced line rather than requested $15,000 given thin file.",
                "standard_applied": "Credit Policy 4.2 — Manual Override on Verified Income Correction"
            },
            "confidence_self_reported": "high", "time_on_decision_ms": 384000
        },
        "ownership": {"owner_type": "individual_decision_maker", "owner_id": "EMP-40219",
                      "role_at_decision": "Senior Credit Analyst II", "override_authority": True},
        "timing": {"decision_at": "2026-07-16T14:22:09Z", "recorded_at": "2026-07-16T14:22:41Z",
                   "permitted_window_minutes": 60, "contemporaneous": True, "reconstructed": False},
        "guard_probe": {"probe_type": "none"},
        "integrity": {},
        "retention": {"retain_until": "2033-07-16", "retention_basis": "ECOA/Reg B adverse action retention plus institutional 7-year credit file policy"}
    }



def boundary_failed_jr(gov_hash):
    """A decision the machine evaluated, failed, and routed to a human."""
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "JR-LEND-2026-0716-004415",
        "record_type": "judgment_record",
        "envelope": {
            "envelope_id": "ENV-CONSUMER-LENDING", "envelope_version": "2.3",
            "workflow": "Consumer Loan Origination — Band A Boundary Referral",
            "reliance_standard_id": "RS-AUTO-APPROVE", "reliance_standard_version": "1.4",
            "trigger": {"escalated": True, "trigger_rule_id": "AUTO-SCORE-FLOOR", "trigger_basis": "threshold_breach"}
        },
        "decision": {"decision_type": "credit_approval_review", "decision_domain": "lending", "risk_tier": "moderate",
                     "subject_ref": "APP-2026-884231", "impact_categories": ["financial", "rights"]},
        "ai_output": {
            "system_id": "CREDIT-SCORE-ENGINE-2", "vendor": "Internal", "model_version": "4.2.1",
            "output_type": "recommendation",
            "recommended_action": "approve",
            "output_summary": "Approve. Composite risk score 739, one point below the auto-approval floor of 740. Requested amount $7,500.",
            "output_value": 739, "confidence_reported": 0.91, "presented_to_human": True
        },
        "boundary_evaluation": {
            "governance_record_id": "GJR-LEND-2026-0102-000007",
            "governance_record_hash": gov_hash,
            "rule_set_id": "RULES-AUTO-APPROVE-BAND-A", "rule_set_version": "1.4",
            "scored_at": "2026-07-16T15:02:10Z",
            "evaluated_at": "2026-07-16T15:02:11Z",
            "routed_to_human_at": "2026-07-16T15:02:11Z",
            "all_conditions_passed": False,
            "condition_results": [
                {"rule_id": "AUTO-ACTION-PERMITTED", "operator": "in", "threshold": ["approve"], "observed_value": "approve", "passed": True},
                {"rule_id": "AUTO-SCORE-FLOOR", "operator": ">=", "threshold": 740, "observed_value": 739, "passed": False},
                {"rule_id": "AUTO-AMOUNT-CEILING", "operator": "<=", "threshold": 10000, "observed_value": 7500, "passed": True},
                {"rule_id": "AUTO-NO-FRAUD-FLAG", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NO-THIN-FILE", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NO-ADVERSE-24MO", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NOT-MANUAL-REFERRAL", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-SCORE-FRESHNESS-HOURS", "operator": "<=", "threshold": 72, "observed_value": 0, "passed": True}
            ],
            "notes": "Failed the auto-approval floor by one point under boundary v1.4. Under v1.3 this application would have auto-executed."
        },
        "human_action": {
            "ai_output_disposition": "accept",
            "final_outcome": "Loan APPROVED at requested $7,500, 36-month term.",
            "reasoning": {
                "tier_a": ["output_within_expected_range", "consistent_with_policy"],
                "tier_b": [{"code": "BAND-A-NEAR-MISS", "label": "Score within 5 points of auto-approval floor, no other adverse factor", "library_version": "2.3"}],
                "narrative": "Referred solely because the score fell one point below the 740 floor introduced by boundary v1.4. All other Band A conditions satisfied. File reviewed in full: income verified, DTI 31%, no derogatory tradelines, 6 years at current employer. No basis to depart from the model recommendation. Approving as recommended.",
                "standard_applied": "Credit Policy 4.0 — Referral Review, Band A Near-Miss"
            },
            "confidence_self_reported": "high", "time_on_decision_ms": 96000
        },
        "ownership": {"owner_type": "individual_decision_maker", "owner_id": "EMP-40221",
                      "role_at_decision": "Credit Analyst I", "override_authority": True},
        "timing": {"decision_at": "2026-07-16T15:14:00Z", "recorded_at": "2026-07-16T15:14:22Z",
                   "permitted_window_minutes": 60, "contemporaneous": True, "reconstructed": False},
        "guard_probe": {"probe_type": "none"},
        "integrity": {},
        "retention": {"retain_until": "2033-07-16", "retention_basis": "Institutional 7-year credit file policy"}
    }


def auto_log(gov_hash):
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "AEL-LEND-2026-0716-004413",
        "record_type": "auto_execution_log",
        "envelope": {
            "envelope_id": "ENV-CONSUMER-LENDING", "envelope_version": "2.3",
            "workflow": "Consumer Loan Origination — Auto-Approval Band",
            "reliance_standard_id": "RS-AUTO-APPROVE", "reliance_standard_version": "1.4",
            "trigger": {"escalated": False, "trigger_rule_id": "TR-AUTO-BAND-A", "trigger_basis": "below_threshold_auto"}
        },
        "decision": {"decision_type": "credit_approval", "decision_domain": "lending", "risk_tier": "low",
                     "subject_ref": "APP-2026-884219", "impact_categories": ["financial"]},
        "ai_output": {
            "system_id": "CREDIT-SCORE-ENGINE-2", "vendor": "Internal", "model_version": "4.2.1",
            "output_type": "recommendation",
            "recommended_action": "approve",
            "output_summary": "Approve. Composite risk score 781, above auto-approval floor of 740. Requested amount $6,000 within Band A ceiling of $10,000.",
            "output_value": 781, "confidence_reported": 0.94, "presented_to_human": False
        },
        "authorizing_boundary": {
            "governance_record_id": "GJR-LEND-2026-0102-000007",
            "governance_record_hash": gov_hash,
            "reliance_standard_id": "RS-AUTO-APPROVE", "reliance_standard_version": "1.4",
            "rule_set_id": "RULES-AUTO-APPROVE-BAND-A", "rule_set_version": "1.4",
            "scored_at": "2026-07-16T14:23:00Z",
            "boundary_evaluated_at": "2026-07-16T14:23:01Z",
            "executed_at": "2026-07-16T14:23:02Z",
            "all_conditions_passed": True,
            "condition_results": [
                {"rule_id": "AUTO-ACTION-PERMITTED", "operator": "in", "threshold": ["approve"], "observed_value": "approve", "passed": True},
                {"rule_id": "AUTO-SCORE-FLOOR", "operator": ">=", "threshold": 740, "observed_value": 781, "passed": True},
                {"rule_id": "AUTO-AMOUNT-CEILING", "operator": "<=", "threshold": 10000, "observed_value": 6000, "passed": True},
                {"rule_id": "AUTO-NO-FRAUD-FLAG", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NO-THIN-FILE", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NO-ADVERSE-24MO", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-NOT-MANUAL-REFERRAL", "operator": "==", "threshold": False, "observed_value": False, "passed": True},
                {"rule_id": "AUTO-SCORE-FRESHNESS-HOURS", "operator": "<=", "threshold": 72, "observed_value": 0, "passed": True}
            ],
            "notes": "Scored, evaluated and executed within two seconds under boundary v1.4, effective 2026-01-05."
        },
        "automated_execution": {
            "executed_action": "approve",
            "execution_summary": "Loan approved automatically at the requested $6,000 amount under the Band A auto-approval boundary."
        },
        "ownership": {"owner_type": "workflow_decision_owner", "owner_id": "EMP-30055",
                      "role_at_decision": "VP Consumer Credit — Decision Owner, ENV-CONSUMER-LENDING",
                      "override_authority": True},
        "timing": {"decision_at": "2026-07-16T14:23:02Z", "recorded_at": "2026-07-16T14:23:02Z",
                   "permitted_window_minutes": 0, "contemporaneous": True, "reconstructed": False},
        "guard_probe": {"probe_type": "none"},
        "integrity": {},
        "retention": {"retain_until": "2033-07-16", "retention_basis": "Institutional 7-year credit file policy"}
    }


def hr_probe():
    return {
        "schema_version": "JA-ES-0.6",
        "record_id": "JR-HR-2026-0611-000318",
        "record_type": "judgment_record",
        "envelope": {
            "envelope_id": "ENV-CONDUCT-ALERTS", "envelope_version": "1.1",
            "workflow": "AI-Flagged Employee Conduct Review",
            "reliance_standard_id": "RS-CONDUCT-TRIAGE", "reliance_standard_version": "1.0",
            "trigger": {"escalated": True, "trigger_rule_id": "TR-HOSTILE-LANG-TIER2", "trigger_basis": "risk_tier"}
        },
        "decision": {"decision_type": "conduct_alert_disposition", "decision_domain": "employment", "risk_tier": "high",
                     "subject_ref": "SEEDCASE-CN-2026-0311", "impact_categories": ["employment", "rights", "reputational"]},
        "ai_output": {
            "system_id": "COMMS-PATTERN-MONITOR", "vendor": "ThirdParty Analytics Inc.", "model_version": "7.0",
            "output_type": "flag",
            "recommended_action": "escalate_for_review",
            "output_summary": "Three emails and two chat threads flagged as consistent with hostile work environment indicators. Severity: Tier 2.",
            "output_value": "tier_2_hostile_indicators", "confidence_reported": 0.71, "presented_to_human": True
        },
        "human_action": {
            "ai_output_disposition": "reject",
            "final_outcome": "Closed without action. No policy violation found. AI flag not sustained.",
            "reasoning": {
                "tier_a": ["contextual_factors_not_visible_to_system", "output_implausible"],
                "tier_b": [{"code": "CONTEXT-PERF-MGMT", "label": "Flagged language occurs within documented performance-management process", "library_version": "1.1"}],
                "narrative": "Reviewed all five flagged items in full thread context. Language is confrontational but directly tied to a documented performance improvement plan issued 2026-05-02 and mirrors standard PIP terminology. No personal, protected-class, or threatening content. No complainant; system-generated only. Closed without action pursuant to Policy 3.2.1.",
                "standard_applied": "Employee Relations Policy 3.2.1 — Threshold for Formal Investigation"
            },
            "confidence_self_reported": "high", "time_on_decision_ms": 1140000
        },
        "ownership": {"owner_type": "individual_decision_maker", "owner_id": "EMP-11784",
                      "role_at_decision": "Senior HR Business Partner", "override_authority": True},
        "timing": {"decision_at": "2026-06-11T10:05:00Z", "recorded_at": "2026-06-11T10:24:00Z",
                   "permitted_window_minutes": 120, "contemporaneous": True, "reconstructed": False},
        "guard_probe": {
            "probe_type": "seeded_case", "probe_id": "SEED-CN-2026-Q2-014", "expected_disposition": "reject",
            "ground_truth_source": "independent_second_line",
            "ground_truth_owner": "Employee Relations Quality Review Panel (independent of HRBP production line)",
            "sandboxed": True, "reviewer_blind_to_probe": True
        },
        "integrity": {},
        "retention": {"retain_until": "2030-06-11", "retention_basis": "Employment records retention policy, 4 years post-disposition"}
    }


def linked_outcome(ref_id, ref_hash):
    r = {
        "schema_version": "JA-ES-LE-0.6",
        "event_id": "LE-OUT-2027-0720-000991", "event_type": "outcome_feedback",
        "references_record_id": ref_id, "references_record_hash": ref_hash,
        "created_at": "2027-07-20T03:15:00Z", "created_by": "SYS-GUARD-OUTCOME-LOADER",
        "outcome_feedback": {
            "outcome_observed_at": "2027-07-20T00:00:00Z", "outcome_label": "no_default_12mo",
            "outcome_source": "Servicing performance file, 12-month origination cohort",
            "observation_window": "12 months from origination", "judgment_assessed_correct": True,
            "assessment_basis": "Loan performed; override of AI decline did not produce loss. Cohort-level override performance reviewed quarterly by second-line credit review."
        },
        "integrity": {}
    }
    r["integrity"] = {"hash_algorithm": "SHA-256", "canonicalization": "RFC8785"}
    c = copy.deepcopy(r); c["integrity"] = {k: v for k, v in c["integrity"].items() if k not in HASH_EXCLUDED}
    r["integrity"]["record_hash"] = hashlib.sha256(rfc8785.dumps(c)).hexdigest()
    return r


def linked_probe_eval(ref_id, ref_hash):
    r = {
        "schema_version": "JA-ES-LE-0.6",
        "event_id": "LE-PRB-2026-0630-000042", "event_type": "probe_evaluation",
        "references_record_id": ref_id, "references_record_hash": ref_hash,
        "created_at": "2026-06-30T16:00:00Z", "created_by": "EMP-22910",
        "probe_evaluation": {
            "probe_id": "SEED-CN-2026-Q2-014", "expected_disposition": "reject", "actual_disposition": "reject",
            "reviewer_passed": True, "evaluator": "Employee Relations Quality Review Panel",
            "evaluator_independent_of_production": True,
            "notes": "Reviewer identified the performance-management context and rejected the flag as designed. Time on decision (19 min) consistent with substantive review."
        },
        "integrity": {"hash_algorithm": "SHA-256", "canonicalization": "RFC8785"}
    }
    c = copy.deepcopy(r); c["integrity"] = {k: v for k, v in c["integrity"].items() if k not in HASH_EXCLUDED}
    r["integrity"]["record_hash"] = hashlib.sha256(rfc8785.dumps(c)).hexdigest()
    return r


def main():
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "examples")
    os.makedirs(out, exist_ok=True)

    g1 = gov_v13()
    h_g1 = seal(g1, GOV_CHAIN, 1, None)

    g2 = gov_v14(h_g1)
    h_g2 = seal(g2, GOV_CHAIN, 2, h_g1)

    jr = lending_jr()
    h_jr = seal(jr, DEC_CHAIN, 1, None)

    bjr = boundary_failed_jr(h_g2)
    h_bjr = seal(bjr, DEC_CHAIN, 2, h_jr)

    ael = auto_log(h_g2)
    seal(ael, DEC_CHAIN, 3, h_bjr)

    hr = hr_probe()
    h_hr = seal(hr, HR_CHAIN, 1, None)

    files = {
        "example-1-governance-boundary-original.json": g1,
        "example-2-governance-boundary-narrowed.json": g2,
        "example-3-lending-decline.json": jr,
        "example-4-boundary-failed-routed-to-human.json": bjr,
        "example-5-auto-execution-log.json": ael,
        "example-6-hr-conduct-seeded-probe.json": hr,
        "example-7-linked-outcome-feedback.json": linked_outcome(jr["record_id"], h_jr),
        "example-8-linked-probe-evaluation.json": linked_probe_eval(hr["record_id"], h_hr),
    }
    for name, rec in files.items():
        with open(os.path.join(out, name), "w") as f:
            json.dump(rec, f, indent=2)
        print(f"wrote {name}")

    print("\nChain verification:")
    for label, recs in [("governance", [g1, g2]), ("lending decisions", [jr, bjr, ael]), ("conduct decisions", [hr])]:
        problems = verify_chain(recs)
        print(f"  {label:20s} {'OK' if not problems else problems}")

    print("\nCross-record links:")
    print(f"  boundary lineage      {'OK' if g2['governance_action']['supersedes_record_hash'] == h_g1 else 'BROKEN'}")
    print(f"  auto-exec authority   {'OK' if ael['authorizing_boundary']['governance_record_hash'] == h_g2 else 'BROKEN'}")


if __name__ == "__main__":
    main()
