"""Golden Set Evaluation Script.

Evaluates RawJsonExtractorAgent & Deadline Extraction against `golden_set.json` across 4 error layers.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from agents import RawJsonExtractorAgent, NvidiaOpenAIClient, normalize_text


def evaluate_golden_set(golden_path: Path) -> Dict[str, Any]:
    if not golden_path.exists():
        return {"error": f"File not found: {golden_path}"}

    testcases: List[Dict[str, Any]] = json.loads(golden_path.read_text(encoding="utf-8"))
    agent = RawJsonExtractorAgent(NvidiaOpenAIClient())

    total = len(testcases)
    passed = 0
    results = []
    layer_stats: Dict[str, Dict[str, int]] = {}

    for tc in testcases:
        tc_id = tc.get("id")
        category = tc.get("category", "Regular")
        text = tc.get("input", "")
        exp = tc.get("expected", {})

        if category not in layer_stats:
            layer_stats[category] = {"total": 0, "passed": 0}
        layer_stats[category]["total"] += 1

        # Test deadline classification
        looks_like_deadline = agent._looks_like_deadline_text(text)
        is_deadline_match = (looks_like_deadline == exp.get("is_deadline"))

        # Test date extraction
        parsed_dt = agent._deadline_from_text(text, "2026-07-30T00:00:00+07:00")
        parsed_date_str = parsed_dt.strftime("%Y-%m-%d %H:%M") if parsed_dt else None
        
        expected_date = exp.get("due_date")
        date_match = True
        if expected_date and parsed_date_str:
            date_match = (parsed_date_str == expected_date)
        elif expected_date and not parsed_date_str:
            date_match = False

        tc_passed = is_deadline_match and date_match
        if tc_passed:
            passed += 1
            layer_stats[category]["passed"] += 1

        results.append({
            "id": tc_id,
            "category": category,
            "description": tc.get("description"),
            "passed": tc_passed,
            "expected_is_deadline": exp.get("is_deadline"),
            "predicted_is_deadline": looks_like_deadline,
            "expected_due_date": expected_date,
            "predicted_due_date": parsed_date_str,
        })

    accuracy = round((passed / total) * 100, 2) if total else 0.0
    return {
        "total_testcases": total,
        "passed_testcases": passed,
        "accuracy_pct": accuracy,
        "layer_breakdown": layer_stats,
        "details": results,
    }


def main() -> None:
    golden_path = Path(__file__).resolve().parent / "golden_set.json"
    report = evaluate_golden_set(golden_path)
    print("=" * 60)
    print(f"📊 GOLDEN SET EVALUATION REPORT ({report.get('total_testcases')} testcases)")
    print("=" * 60)
    print(f"✅ Overall Accuracy: {report.get('accuracy_pct')}% ({report.get('passed_testcases')}/{report.get('total_testcases')})\n")
    print("📁 Breakdown by Category Layer:")
    for layer, stats in report.get("layer_breakdown", {}).items():
        pct = round((stats['passed'] / stats['total']) * 100, 1) if stats['total'] else 0
        print(f"  • {layer:<25}: {stats['passed']}/{stats['total']} ({pct}%)")
    print("=" * 60)


if __name__ == "__main__":
    main()
