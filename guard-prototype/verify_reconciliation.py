#!/usr/bin/env python3
"""
JA Guard reconciliation verifier (PROTOTYPE).

Recomputes the reconciliation from the retained manifests rather than trusting
the record's own assertions. Checks:

  1. schema validity
  2. record hash
  3. each manifest's own digest, and that it matches the digest asserted in the record
  4. recorded_population digest recomputed over the UNION of auto + routed
  5. partition_digest_matches recomputed, not read
  6. exception sets recomputed by set difference against the manifests
  7. anchors: 64-hex, externally retained, custodian cannot modify

The point of 4-6: a reconciliation that reports its own result is an assertion.
A reconciliation whose result can be recomputed from independently retained
manifests is evidence.

Requires: pip install jsonschema rfc8785
"""
import json, sys, os, hashlib, copy
import jsonschema, rfc8785

HERE = os.path.dirname(os.path.abspath(__file__))


def load(p):
    with open(p) as f:
        return json.load(f)


def digest_ids(ids):
    """sha256-of-rfc8785-canonical-sorted-unique-id-array"""
    return hashlib.sha256(rfc8785.dumps(sorted(set(ids)))).hexdigest()


def record_hash(rec):
    c = copy.deepcopy(rec)
    c["integrity"] = {k: v for k, v in c["integrity"].items() if k not in ("record_hash", "signature")}
    return hashlib.sha256(rfc8785.dumps(c)).hexdigest()


def resolve(loc):
    """Manifest locations are recorded relative to the package root."""
    for cand in (os.path.join(HERE, os.path.basename(os.path.dirname(loc)), os.path.basename(loc)),
                 os.path.join(HERE, loc), loc):
        if os.path.exists(cand):
            return cand
    return None


def verify(path):
    rec = load(path)
    problems, notes = [], []

    schema = load(os.path.join(HERE, "reconciliation.schema.json"))
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(rec))
    if errs:
        return [f"[schema]   {e.message[:140]}" for e in errs], notes

    if record_hash(rec) != rec["integrity"]["record_hash"]:
        problems.append("[integrity] record_hash does not match recomputed hash")

    sets, ids = rec["sets"], {}
    for name in ("evaluated", "auto_executed", "routed_to_human"):
        s = sets[name]
        man = s.get("manifest")
        if not man:
            problems.append(f"[manifest]  {name}: no manifest — digest is unfalsifiable, nobody can recompute it")
            continue
        p = resolve(man["location"])
        if not p:
            problems.append(f"[manifest]  {name}: manifest not retrievable at {man['location']}")
            continue
        raw = open(p, "rb").read()
        if hashlib.sha256(raw).hexdigest() != man["manifest_digest"]:
            problems.append(f"[manifest]  {name}: manifest file digest does not match the record")
            continue
        body = json.loads(raw)
        ids[name] = body["identifiers"]
        if digest_ids(ids[name]) != s["digest"]:
            problems.append(f"[digest]    {name}: recomputed digest does not match the asserted digest")
        if len(set(ids[name])) != s["count"]:
            problems.append(f"[count]     {name}: manifest holds {len(set(ids[name]))}, record asserts {s['count']}")

    if len(ids) == 3:
        union = set(ids["auto_executed"]) | set(ids["routed_to_human"])
        overlap = set(ids["auto_executed"]) & set(ids["routed_to_human"])
        if overlap:
            problems.append(f"[partition] {len(overlap)} identifier(s) appear in BOTH auto-executed and routed sets")

        rp = sets["recorded_population"]
        if digest_ids(union) != rp["digest"]:
            problems.append("[union]     recorded_population digest does not match the union of auto + routed")
        if len(union) != rp["count"]:
            problems.append(f"[union]     recorded_population count {rp['count']} != union size {len(union)}")

        recomputed = digest_ids(union) == digest_ids(ids["evaluated"])
        if recomputed != sets["partition_digest_matches"]:
            problems.append(f"[assertion] partition_digest_matches asserts {sets['partition_digest_matches']}, recomputes to {recomputed}")

        ev = set(ids["evaluated"])
        missing, orphan = sorted(ev - union), sorted(union - ev)
        for key, computed in (("missing", missing), ("orphan", orphan)):
            asserted = rec["exceptions"][key]
            if asserted["count"] != len(computed):
                problems.append(f"[exception] {key}: record asserts {asserted['count']}, manifests show {len(computed)}")
            elif not asserted.get("identifiers_truncated") and sorted(asserted["identifiers"]) != computed:
                problems.append(f"[exception] {key}: identifiers do not match those computed from manifests")

        if not recomputed:
            notes.append(f"reconciliation FAILED as recorded: {len(missing)} missing, {len(orphan)} orphan")
            notes.append(f"counts alone: evaluated {len(ev)}, recorded {len(union)} — "
                         f"{'IDENTICAL, so an arithmetic check would have passed' if len(ev) == len(union) else 'differ'}")

    for a in rec["chain_anchors"]:
        if a.get("externally_anchored"):
            an = a.get("anchor", {})
            if an.get("custodian_can_modify"):
                problems.append(f"[anchor]    {a['chain_id']}: custodian can modify the anchor — regeneration gap not closed")
            if an.get("independently_retrievable_digest") and an["independently_retrievable_digest"] != a["head_record_hash"]:
                problems.append(f"[anchor]    {a['chain_id']}: independently retrievable digest differs from the recorded head")
        else:
            notes.append(f"chain {a['chain_id']} is not externally anchored — truncation remains undetectable")

    return problems, notes


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "example-reconciliation-with-exceptions.json")
    problems, notes = verify(path)
    print(f"JA Guard reconciliation verification — {os.path.basename(path)}\n")
    for n in notes:
        print(f"  note: {n}")
    if notes:
        print()
    if problems:
        print(f"VERIFICATION FAILED — {len(problems)} problem(s):")
        for p in problems:
            print("  " + p)
        return 1
    print("VERIFICATION PASSED — the record's reconciliation result is reproducible from the retained manifests.")
    print("(A failed reconciliation that is honestly reported and reproducible passes verification.")
    print(" Verification asks whether the control operated and reported truthfully, not whether it found nothing.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
