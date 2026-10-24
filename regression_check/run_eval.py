#!/usr/bin/env python3
"""
Regression check for the HCP CRM agent.

Question it answers: "Did my last prompt/model change make the system worse?"

It runs 25 fixed cases against the REAL code in backend/app/agent and scores them
with deterministic rules (no LLM-as-judge), in three suites:
  1. extraction  - log_interaction's EXTRACTION_PROMPT -> correct fields
  2. compliance  - flag_compliance_risk -> flags AE / off-label / promissory text,
                   and does NOT flag clean notes (misses here are safety-critical)
  3. routing     - the main SYSTEM_PROMPT -> agent picks the right tool

Usage (from the backend/ folder, with GROQ_API_KEY set):
  python ../regression_check/run_eval.py --label v1_first_prompt
  python ../regression_check/run_eval.py --label v2_current --baseline results_v1_first_prompt.json

Exit code is 1 if any previously-passing case now fails (a regression), so it can
gate a change. Results are saved to results_<label>.json next to this script.
"""
import argparse, json, os, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Use a throwaway SQLite DB so the check never touches real CRM data.
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
sys.path.insert(0, os.getcwd())  # run from backend/ so `app` imports resolve


def check_extraction(case, extract_fn):
    got = extract_fn(case["note"])
    e, fails = case["expect"], []
    low = lambda v: (v or "").lower()
    if "hcp_name_contains" in e and e["hcp_name_contains"] not in low(got.get("hcp_name")):
        fails.append(f"hcp_name={got.get('hcp_name')!r}")
    if "interaction_type" in e and got.get("interaction_type") != e["interaction_type"]:
        fails.append(f"interaction_type={got.get('interaction_type')!r}")
    if "sentiment" in e and got.get("sentiment") != e["sentiment"]:
        fails.append(f"sentiment={got.get('sentiment')!r}")
    if "materials_contains" in e and not any(e["materials_contains"] in low(m) for m in (got.get("materials_shared") or [])):
        fails.append(f"materials={got.get('materials_shared')!r}")
    if e.get("hcp_name_empty") and (got.get("hcp_name") or "").strip().lower() not in ("", "none", "null", "unknown", "unknown hcp", "n/a"):
        fails.append(f"invented hcp_name={got.get('hcp_name')!r}")
    if e.get("samples_nonempty") and not got.get("samples_distributed"):
        fails.append("samples empty")
    if e.get("materials_nonempty") and not got.get("materials_shared"):
        fails.append("materials empty")
    if e.get("outcomes_nonempty") and not got.get("outcomes"):
        fails.append("outcomes empty")
    if e.get("samples_empty") and got.get("samples_distributed"):
        fails.append(f"invented samples={got.get('samples_distributed')!r}")
    if e.get("materials_empty") and got.get("materials_shared"):
        fails.append(f"invented materials={got.get('materials_shared')!r}")
    if not got:
        fails.append("JSON parse failed (empty result)")
    return fails


def check_compliance(case, tool):
    out = json.loads(tool.invoke({"text": case["text"]}))
    flagged = bool(out.get("flags"))
    if case["expect_flag"] and not flagged:
        return ["MISSED a risk (false negative)"]
    if not case["expect_flag"] and flagged:
        return [f"false alarm: {out['flags']}"]
    return []


def check_routing(case, run_agent):
    _, tool_calls = run_agent(case["message"], thread_id=f"eval-{case['id']}")
    if case.get("expect_no_tool"):
        return [] if not tool_calls else [f"should call no tool, called {sorted(set(tool_calls))}"]
    return [] if case["expect_tool"] in tool_calls else [f"called {sorted(set(tool_calls))}, wanted {case['expect_tool']}"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True, help="name for this run, e.g. v1_first_prompt")
    ap.add_argument("--baseline", help="results_*.json from an earlier run to compare against")
    args = ap.parse_args()

    from app.database import Base, engine, SessionLocal
    from app.models import Interaction
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()  # seed one record so edit / follow-up / history cases have a target
    db.add(Interaction(hcp_name="Dr. Seed", interaction_type="Meeting", interaction_date="2026-10-01",
                       interaction_time="10:00", topics_discussed="Prodo-X efficacy", sentiment="Positive",
                       outcomes="", materials_shared=[], samples_distributed=[], follow_up_actions=[],
                       compliance_flags=[], source="form", raw_input="seed"))
    db.commit(); db.close()

    from app.agent import tools as T
    from app.agent.graph import run_agent
    extract = lambda note: T._safe_json_parse(T.get_default_llm().invoke(T.EXTRACTION_PROMPT.format(note=note)).content)

    cases = json.loads((HERE / "cases.json").read_text())
    results = {}
    for suite, runner in (("extraction", lambda c: check_extraction(c, extract)),
                          ("compliance", lambda c: check_compliance(c, T.flag_compliance_risk)),
                          ("routing", lambda c: check_routing(c, run_agent))):
        for c in cases[suite]:
            try:
                fails = runner(c)
            except Exception as ex:  # an API/model error counts as a failure, loudly
                fails = [f"ERROR {type(ex).__name__}: {ex}"]
            results[f"{suite}:{c['id']}"] = {"pass": not fails, "why": fails}
            print(f"{'PASS' if not fails else 'FAIL'}  {suite}:{c['id']}  {'; '.join(fails)}")

    passed = sum(r["pass"] for r in results.values())
    print(f"\n{args.label}: {passed}/{len(results)} passed")
    for suite in cases:
        s = [r for k, r in results.items() if k.startswith(suite + ":")]
        print(f"  {suite:11s} {sum(r['pass'] for r in s)}/{len(s)}")
    (HERE / f"results_{args.label}.json").write_text(json.dumps(results, indent=2))

    if args.baseline:
        base = json.loads(Path(args.baseline).read_text() if Path(args.baseline).exists() else (HERE / args.baseline).read_text())
        regress = [k for k, r in base.items() if r["pass"] and not results.get(k, {}).get("pass")]
        fixed = [k for k, r in base.items() if not r["pass"] and results.get(k, {}).get("pass")]
        print(f"\nvs baseline: {len(fixed)} fixed, {len(regress)} REGRESSED")
        for k in regress: print("  REGRESSION:", k, results[k]["why"])
        sys.exit(1 if regress else 0)


if __name__ == "__main__":
    main()
