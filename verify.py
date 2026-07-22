#!/usr/bin/env python3
"""
JA-ES verifier — checks what a schema validator cannot.

Three layers:
  1. schema      — is the record well-formed
  2. integrity   — does record_hash match the recomputed hash; is the chain intact
  3. links       — do cross-record references resolve to the sealed hashes

Layer 1 alone is not verification. A fabricated record with a rewritten
rationale passes schema validation; it fails layer 2.

Usage:
    python verify.py --self-test      # reproduce the published test vectors first
    python verify.py examples/

Requires: pip install jsonschema rfc8785
"""
import json, sys, os, glob, hashlib, copy
import jsonschema, rfc8785

HERE = os.path.dirname(os.path.abspath(__file__))
HASH_EXCLUDED = ("record_hash", "signature")


def load(p):
    with open(p) as f:
        return json.load(f)


def compute_hash(record):
    c = copy.deepcopy(record)
    c["integrity"] = {k: v for k, v in c["integrity"].items() if k not in HASH_EXCLUDED}
    return hashlib.sha256(rfc8785.dumps(c)).hexdigest()


def is_linked_event(r):
    return str(r.get("schema_version", "")).startswith("JA-ES-LE")


def verify(directory):
    ev = jsonschema.Draft202012Validator(load(os.path.join(HERE, "evidence-record.schema.json")))
    le = jsonschema.Draft202012Validator(load(os.path.join(HERE, "linked-event.schema.json")))

    records, events, problems = [], [], []

    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        name = os.path.basename(path)
        r = load(path)
        # Manifests and other suite metadata may be JSON arrays. They are not
        # JA-ES records and must not be passed to object-oriented validators.
        if not isinstance(r, dict):
            continue
        validator = le if is_linked_event(r) else ev

        errs = list(validator.iter_errors(r))
        if errs:
            problems.append(f"[schema]    {name}: {errs[0].message[:120]}")
            continue

        if compute_hash(r) != r["integrity"]["record_hash"]:
            problems.append(f"[integrity] {name}: record_hash does not match recomputed hash — record altered after sealing")

        (events if is_linked_event(r) else records).append((name, r))

    # chains
    chains = {}
    for name, r in records:
        chains.setdefault(r["integrity"]["chain_id"], []).append((name, r))

    for chain_id, items in sorted(chains.items()):
        items.sort(key=lambda x: x[1]["integrity"]["sequence"])
        prev_hash, expected = None, 1
        for name, r in items:
            integ = r["integrity"]
            if integ["sequence"] != expected:
                problems.append(f"[chain]     {name}: sequence {integ['sequence']}, expected {expected} in '{chain_id}' — deleted record")
            if prev_hash is None:
                if not integ.get("chain_genesis"):
                    problems.append(f"[chain]     {name}: first in '{chain_id}' but chain_genesis not set")
            elif integ.get("prev_record_hash") != prev_hash:
                problems.append(f"[chain]     {name}: prev_record_hash does not match prior record in '{chain_id}' — chain broken")
            prev_hash = integ["record_hash"]
            expected = integ["sequence"] + 1

    by_id = {r["record_id"]: r for _, r in records}

    # cross-record links
    for name, r in records:
        ab = r.get("authorizing_boundary")
        if ab:
            gid, ghash = ab["governance_record_id"], ab["governance_record_hash"]
            gov = by_id.get(gid)
            if gov is None:
                problems.append(f"[link]      {name}: authorizing boundary {gid} not present in this set (cannot verify)")
            elif gov["integrity"]["record_hash"] != ghash:
                problems.append(f"[link]      {name}: authorizing boundary hash does not match {gid} — authority substituted")
            elif gov["record_type"] != "governance_judgment_record":
                problems.append(f"[link]      {name}: authorizing record {gid} is not a governance judgment record")
            else:
                permitted = gov["boundary_scope"].get("permitted_automated_actions", [])
                prohibited = gov["boundary_scope"].get("prohibited_automated_actions", [])
                executed = r.get("automated_execution", {}).get("executed_action")
                recommended = r.get("ai_output", {}).get("recommended_action")
                if executed not in permitted:
                    problems.append(f"[action]    {name}: executed action '{executed}' is not permitted by {gid}")
                if executed in prohibited:
                    problems.append(f"[action]    {name}: executed action '{executed}' is expressly prohibited by {gid}")
                if recommended != executed:
                    problems.append(f"[action]    {name}: recommended action '{recommended}' does not match executed action '{executed}'")
                action_results = [c for c in ab.get("condition_results", []) if c.get("rule_id") == "AUTO-ACTION-PERMITTED"]
                if len(action_results) != 1:
                    problems.append(f"[action]    {name}: expected exactly one AUTO-ACTION-PERMITTED condition result")
                else:
                    action_result = action_results[0]
                    if action_result.get("observed_value") != executed or action_result.get("passed") is not True:
                        problems.append(f"[action]    {name}: AUTO-ACTION-PERMITTED does not affirm the executed action")
                    threshold = action_result.get("threshold")
                    if not isinstance(threshold, list) or set(threshold) != set(permitted):
                        problems.append(f"[action]    {name}: AUTO-ACTION-PERMITTED threshold does not match the sealed permitted action set")

        be = r.get("boundary_evaluation")
        if be:
            gid, ghash = be["governance_record_id"], be["governance_record_hash"]
            gov = by_id.get(gid)
            if gov is None:
                problems.append(f"[link]      {name}: evaluated boundary {gid} not present in this set (cannot verify)")
            elif gov["integrity"]["record_hash"] != ghash:
                problems.append(f"[link]      {name}: evaluated boundary hash does not match {gid} — boundary substituted")

        ga = r.get("governance_action", {})
        if "supersedes_record_id" in ga:
            pid, phash = ga["supersedes_record_id"], ga.get("supersedes_record_hash")
            prior = by_id.get(pid)
            if prior is None:
                problems.append(f"[link]      {name}: superseded boundary {pid} not present in this set (cannot verify)")
            elif prior["integrity"]["record_hash"] != phash:
                problems.append(f"[link]      {name}: superseded boundary hash does not match {pid} — lineage substituted")

    for name, e in events:
        rid, rhash = e["references_record_id"], e["references_record_hash"]
        target = by_id.get(rid)
        if target is None:
            problems.append(f"[link]      {name}: referenced record {rid} not present in this set (cannot verify)")
        elif target["integrity"]["record_hash"] != rhash:
            problems.append(f"[link]      {name}: referenced record hash does not match {rid} — original substituted")

    return records, events, chains, problems


def self_test():
    """Reproduce the published test vectors. Run this before trusting any implementation."""
    path = os.path.join(HERE, "test-vectors.json")
    if not os.path.exists(path):
        print("test-vectors.json not found"); return 1
    tv = load(path)
    print(f"JA-ES self-test — {tv['canonicalization']} + {tv['hash_algorithm']}")
    failed = 0
    for v in tv["vectors"]:
        if "input" in v:
            canon = rfc8785.dumps(v["input"]).decode()
            got = hashlib.sha256(canon.encode()).hexdigest()
            if canon != v["canonical_form"]:
                print(f"  FAIL  {v['name']}: canonical form differs")
                print(f"        expected {v['canonical_form']}")
                print(f"        got      {canon}")
                failed += 1
                continue
        else:
            rec = load(os.path.join(HERE, v["input_file"]))
            got = compute_hash(rec)
            if got != rec["integrity"]["record_hash"]:
                print(f"  FAIL  {v['name']}: does not match the record's sealed hash")
                failed += 1
                continue
        status = "ok" if got == v["sha256"] else "FAIL"
        if status == "FAIL":
            failed += 1
            print(f"  FAIL  {v['name']}\n        expected {v['sha256']}\n        got      {got}")
        else:
            print(f"  ok    {v['name']}")
    print()
    if failed:
        print(f"SELF-TEST FAILED — {failed} vector(s). This implementation must not be used to seal or verify records.")
        return 1
    print("SELF-TEST PASSED — canonicalization and hashing agree with the published vectors.")
    return 0


def print_report(directory, records, events, chains, problems):
    if not records and not events and not problems:
        problems.append("[input]     no JA-ES records or linked events found — nothing was verified")

    print(f"JA-ES verification — {directory}")
    print(f"  evidence records : {len(records)}")
    print(f"  linked events    : {len(events)}")
    print(f"  chains           : {', '.join(f'{k} (n={len(v)})' for k, v in sorted(chains.items())) or 'none'}")
    print()
    if problems:
        print(f"FAILED — {len(problems)} problem(s):")
        for p in problems:
            print("  " + p)
        return 1
    print("PASSED — schema valid, all hashes verify, chains intact, all cross-record links resolve.")
    return 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    directory = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "examples")
    if not os.path.isdir(directory):
        print(f"FAILED — input directory not found: {directory}")
        return 1

    # A suite directory may contain independent scenario subdirectories, as
    # test-action-verification/ does. Verify each scenario independently so
    # duplicate record IDs and chain sequences do not contaminate one another.
    top_level_json = glob.glob(os.path.join(directory, "*.json"))
    scenario_dirs = sorted(
        d for d in glob.glob(os.path.join(directory, "*"))
        if os.path.isdir(d) and glob.glob(os.path.join(d, "*.json"))
    )
    if not top_level_json and scenario_dirs:
        failed = 0
        for index, scenario in enumerate(scenario_dirs):
            if index:
                print()
            failed += print_report(scenario, *verify(scenario))
        return 1 if failed else 0

    return print_report(directory, *verify(directory))


if __name__ == "__main__":
    sys.exit(main())
