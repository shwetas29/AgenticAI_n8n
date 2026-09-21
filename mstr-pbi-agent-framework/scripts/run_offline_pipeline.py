#!/usr/bin/env python3
"""
Offline runner for the MSTR→PBI agent framework.

Simulates the n8n control loop with deterministic assess/classify plus
catalogue-driven blueprint stubs. Use this to validate contracts without n8n.
LLM calls are optional via OPENAI_API_KEY.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "samples"
MAPPINGS = ROOT / "mappings" / "pattern-catalogue.json"
POLICY = ROOT / "config" / "classification-policy.json"
OUT = ROOT / "out"


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def match_patterns(intake: dict, catalogue: dict) -> list[str]:
    text = json.dumps(intake).lower()
    matched = []
    rules = [
        ("crosstab" in text or intake.get("type") == "grid", "PAT-GRID-MATRIX"),
        ("margin" in text or "%" in text, "PAT-METRIC-RATIO"),
        ("threshold" in text or "shading" in text, "PAT-CONDITIONAL-FORMAT"),
        ("subtotal" in text, "PAT-SUBTOTALS"),
        (intake.get("type") == "dossier" or "pages" in (intake.get("layout") or {}), "PAT-DOSSIER-PAGES"),
        ("apply-to-all" in text or "apply to all" in text, "PAT-APPLY-TO-ALL"),
        (bool(intake.get("drillPaths")), "PAT-DRILL-PATH"),
        ("kpi" in text, "PAT-KPI-TREND"),
        (any(f.get("kind") == "prompt" for f in intake.get("filters", [])), "PAT-PROMPT-DATE"),
        (any(f.get("kind") == "securityFilter" for f in intake.get("filters", [])), "PAT-SECURITY-FILTER"),
        (any(f.get("kind") == "topN" for f in intake.get("filters", [])), "PAT-TOPN-WITHIN-RLS"),
    ]
    for cond, pid in rules:
        if cond and pid not in matched:
            matched.append(pid)
    # Always consider star-schema remap for grids/dossiers
    if intake.get("type") in {"grid", "dossier"} and "PAT-SNOWFLAKE-TO-STAR" not in matched:
        matched.append("PAT-SNOWFLAKE-TO-STAR")
    known = {p["id"] for p in catalogue["patterns"]}
    return [p for p in matched if p in known]


def assess(intake: dict, matched: list[str], catalogue: dict) -> dict:
    flags = []
    if "PAT-SUBTOTALS" in matched:
        flags.append("grid_subtotals")
    if "PAT-PROMPT-DATE" in matched:
        flags.append("prompt_query_shaping")
    if "PAT-SECURITY-FILTER" in matched:
        flags.append("security_filter")
    if "PAT-TOPN-WITHIN-RLS" in matched:
        flags.append("topn_within_security")
    if "PAT-APPLY-TO-ALL" in matched:
        flags.append("multi_page_sync")
    if "PAT-DRILL-PATH" in matched:
        flags.append("custom_drill")

    pattern_meta = {p["id"]: p for p in catalogue["patterns"]}
    review_patterns = sum(1 for p in matched if pattern_meta.get(p, {}).get("requiresReview"))
    auto_high = sum(1 for p in matched if pattern_meta.get(p, {}).get("automation") == "high")

    pages = len((intake.get("layout") or {}).get("pages") or [])
    complexity = min(
        100,
        12
        + 6 * len(intake.get("metrics", []))
        + 6 * max(pages - 1, 0)
        + 8 * len(intake.get("drillPaths") or [])
        + 10 * review_patterns,
    )
    semantic = min(100, 10 + 25 * ("grid_subtotals" in flags) + 30 * ("topn_within_security" in flags) + 15 * ("prompt_query_shaping" in flags))
    security = min(100, 5 + 55 * ("security_filter" in flags) + 20 * ("topn_within_security" in flags))
    ux = min(100, 10 + 25 * ("multi_page_sync" in flags) + 20 * ("prompt_query_shaping" in flags) + 15 * ("custom_drill" in flags))
    # Catalogue coverage dominates automation fit; review-only patterns reduce but do not zero it.
    automation_fit = max(
        0,
        min(100, int(55 + 45 * (auto_high / max(len(matched), 1)) - 15 * review_patterns)),
    )

    if security >= 40 or review_patterns:
        lane = "review"
    elif complexity > 75 and automation_fit < 45:
        lane = "hand_build"
    else:
        lane = "automate"

    return {
        "reportId": intake["reportId"],
        "scores": {
            "complexity": complexity,
            "semanticRisk": semantic,
            "securityRisk": security,
            "uxRisk": ux,
            "automationFit": automation_fit,
        },
        "drivers": [
            {"dimension": "patterns", "finding": f"Matched {matched}", "severity": "info"},
            *[{"dimension": "risk", "finding": f, "severity": "warn"} for f in flags],
        ],
        "riskFlags": flags,
        "matchedPatterns": matched,
        "laneRecommendation": lane,
        "assessorNotes": "Deterministic offline assessor (n8n LLM agent can refine).",
    }


def classify(intake: dict, assessment: dict, policy: dict) -> dict:
    flags = set(assessment["riskFlags"])
    force_review = bool(flags.intersection(policy["forceReviewFlags"]))
    usage = intake.get("usage") or {}
    criticality = usage.get("criticality", "low")
    executions = usage.get("executionsLast90Days", 0)

    if executions == 0 and criticality == "low":
        disposition, rule = "RETIRE", "unused_low_criticality"
    elif criticality == "regulatory" and assessment["scores"]["automationFit"] < 35 and assessment["laneRecommendation"] == "hand_build":
        disposition, rule = "REDESIGN", "regulatory_low_automation"
    elif assessment["laneRecommendation"] == "hand_build" and assessment["scores"]["automationFit"] < 40:
        disposition, rule = "REDESIGN", "hand_build_lane"
    else:
        disposition, rule = "MIGRATE", "default_migrate"

    requires = force_review or disposition in {"RETIRE", "CONSOLIDATE", "REDESIGN"} or assessment["scores"]["securityRisk"] >= 40
    if criticality in {"high", "regulatory"} and usage.get("monthlyActiveUsers", 0) > 50:
        priority = "P0"
    elif criticality in {"high", "regulatory"}:
        priority = "P1"
    elif usage.get("monthlyActiveUsers", 0) > 30:
        priority = "P2"
    else:
        priority = "P3"

    wave = "W1" if disposition == "MIGRATE" and not force_review else ("W3" if disposition == "REDESIGN" else "W2")

    return {
        "reportId": intake["reportId"],
        "disposition": disposition,
        "priority": priority,
        "wave": wave,
        "rationale": f"Rule={rule}; lane={assessment['laneRecommendation']}; flags={sorted(flags)}",
        "requiresHumanApproval": requires,
        "approvalReasons": (
            [f"force_review:{f}" for f in sorted(flags.intersection(policy["forceReviewFlags"]))]
            + ([f"disposition:{disposition}"] if disposition != "MIGRATE" else [])
        ),
    }


def attach_expected_blueprint(report_id: str) -> dict | None:
    for sample_dir in SAMPLES.iterdir():
        if not sample_dir.is_dir():
            continue
        bp = sample_dir / "expected-blueprint.json"
        if bp.exists():
            data = load_json(bp)
            if data.get("reportId") == report_id:
                return data
    return None


def validate_plan(intake: dict, blueprint: dict) -> dict:
    checks = [
        {
            "id": "DATA-01",
            "category": "data",
            "description": "Reconcile Revenue/Sales totals for last complete month vs MSTR extract",
            "method": "SQL/DAX side-by-side within 0.1% tolerance",
            "owner": "automation",
            "severity": "blocker",
            "status": "pending",
        },
        {
            "id": "MET-01",
            "category": "metrics",
            "description": "Validate ratio measures use DIVIDE of components at subtotal grain",
            "method": "Matrix subtotal spot checks",
            "owner": "analyst",
            "severity": "major",
            "status": "pending",
        },
        {
            "id": "BEH-01",
            "category": "behaviour",
            "description": "Confirm filter/prompt/TopN behaviour matches agreed UX",
            "method": "Scripted UI scenarios",
            "owner": "analyst",
            "severity": "major",
            "status": "pending",
        },
        {
            "id": "SEC-01",
            "category": "security",
            "description": "RLS leakage test for two personas",
            "method": "View as role / UPN test",
            "owner": "security",
            "severity": "blocker" if blueprint.get("security", {}).get("requiresSecurityReview") else "minor",
            "status": "pending",
        },
        {
            "id": "PERF-01",
            "category": "performance",
            "description": "Page load and refresh under expected concurrency",
            "method": "Perf analyzer + capacity metrics",
            "owner": "analyst",
            "severity": "minor",
            "status": "pending",
        },
    ]
    return {
        "reportId": intake["reportId"],
        "checks": checks,
        "exitCriteria": [
            "No material data discrepancy on certified metrics",
            "Security validated for representative users",
            "Performance acceptable",
            "Business sign-off recorded",
        ],
        "cutoverStage": "pilot" if intake["reportId"].startswith("sample-") else "parallel",
    }


def certify(bundle: dict) -> dict:
    needs_sec = bundle["blueprint"]["security"].get("requiresSecurityReview")
    blocked = needs_sec and bundle["classification"]["requiresHumanApproval"]
    # Offline: ready for signoff if not security-blocked; still not auto-certified
    status = "blocked" if blocked and not bundle.get("approvals", {}).get("security") else "ready_for_signoff"
    if bundle.get("approvals", {}).get("business"):
        status = "certified"
    return {
        "reportId": bundle["intake"]["reportId"],
        "certificationStatus": status,
        "summary": f"{bundle['classification']['disposition']} via {bundle['assessment']['laneRecommendation']} lane",
        "evidenceIndex": [
            "inventory",
            "assessment",
            "classification",
            "blueprint",
            "validation-plan",
        ],
        "residualRisks": bundle["blueprint"].get("openQuestions", []),
        "releaseNotes": "Offline dry-run pack generated by framework runner.",
        "signOffRequiredFrom": (
            ["security", "business"] if needs_sec else ["business"]
        ),
        "rollbackNotes": "Retain MSTR object published until parallel period ends; disable PBI app audience if defect severity=blocker.",
    }


def run_one(intake_path: Path, approve: bool = False) -> dict:
    intake = load_json(intake_path)
    catalogue = load_json(MAPPINGS)
    policy = load_json(POLICY)
    matched = match_patterns(intake, catalogue)
    assessment = assess(intake, matched, catalogue)
    classification = classify(intake, assessment, policy)
    blueprint = attach_expected_blueprint(intake["reportId"])
    if blueprint is None:
        blueprint = {
            "reportId": intake["reportId"],
            "targetPlatform": "fabric",
            "semanticModel": {"name": f"Model for {intake['name']}", "mode": "directlake", "tables": [], "relationships": []},
            "measures": [],
            "reportPages": [],
            "security": {"rlsRoles": [], "requiresSecurityReview": "security_filter" in assessment["riskFlags"]},
            "uxNotes": "Stub blueprint — run Transformer agent in n8n for full draft.",
            "openQuestions": ["No expected-blueprint.json for this reportId"],
            "buildLane": assessment["laneRecommendation"],
        }
    validation = validate_plan(intake, blueprint)
    bundle = {
        "intake": intake,
        "assessment": assessment,
        "classification": classification,
        "blueprint": blueprint,
        "validation": validation,
        "approvals": {"security": approve, "business": approve},
        "decisionLog": [
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "stage": stage,
                "reportId": intake["reportId"],
            }
            for stage in ["discover", "assess", "classify", "transform", "validate", "certify"]
        ],
    }
    if classification["requiresHumanApproval"] and not approve:
        bundle["hitl"] = {
            "status": "awaiting_approval",
            "reasons": classification["approvalReasons"],
        }
        bundle["certification"] = {
            "reportId": intake["reportId"],
            "certificationStatus": "blocked",
            "summary": "Paused at HITL gate",
            "evidenceIndex": ["inventory", "assessment", "classification"],
            "residualRisks": classification["approvalReasons"],
            "releaseNotes": "",
            "signOffRequiredFrom": ["migration.lead"],
            "rollbackNotes": "N/A — not released",
        }
    else:
        bundle["hitl"] = {"status": "approved" if approve else "not_required"}
        bundle["certification"] = certify(bundle)
    return bundle


def main():
    parser = argparse.ArgumentParser(description="Run MSTR→PBI agent control loop offline")
    parser.add_argument("--sample", choices=["a", "b", "c", "all"], default="all")
    parser.add_argument("--approve", action="store_true", help="Simulate HITL approvals")
    args = parser.parse_args()

    mapping = {
        "a": SAMPLES / "sample-a-regional-sales" / "intake.json",
        "b": SAMPLES / "sample-b-store-operations" / "intake.json",
        "c": SAMPLES / "sample-c-category-manager" / "intake.json",
    }
    paths = list(mapping.values()) if args.sample == "all" else [mapping[args.sample]]
    OUT.mkdir(parents=True, exist_ok=True)

    summary = []
    for path in paths:
        bundle = run_one(path, approve=args.approve)
        out_path = OUT / f"{bundle['intake']['reportId']}.bundle.json"
        out_path.write_text(json.dumps(bundle, indent=2))
        summary.append(
            {
                "reportId": bundle["intake"]["reportId"],
                "disposition": bundle["classification"]["disposition"],
                "lane": bundle["assessment"]["laneRecommendation"],
                "hitl": bundle["hitl"]["status"],
                "certification": bundle["certification"]["certificationStatus"],
                "out": str(out_path),
            }
        )
        print(json.dumps(summary[-1], indent=2))

    (OUT / "run-summary.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
