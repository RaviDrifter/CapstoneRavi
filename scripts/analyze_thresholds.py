"""Evaluate routing/answerability thresholds using labelled validation tickets only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.classify import MANDATORY_ESCALATION_INTENTS, get_classifier
from src.config import DATA_DIR
from src.guardrails import detect_prompt_injection
from src.ingest import normalize_ticket
from src.retrieve import get_retriever
from src.routing import human_review_override


def evaluate(input_path: Path, route_thresholds: list[float], answerability_thresholds: list[float]) -> dict[str, Any]:
    tickets = json.loads(input_path.read_text(encoding="utf-8"))
    classifier = get_classifier()
    retriever = get_retriever()
    prepared = []
    for index, raw in enumerate(tickets):
        ticket = normalize_ticket(raw, index)
        classification = classifier.classify(ticket)
        sources = retriever.search(ticket.get("text", ""), top_k=5)
        prepared.append((raw, ticket, classification, sources))

    rows = []
    for route_threshold in route_thresholds:
        for answerability_threshold in answerability_thresholds:
            predictions = []
            for raw, ticket, classification, sources in prepared:
                if detect_prompt_injection(ticket.get("text", "")):
                    decision = "escalate"
                elif not ticket.get("text", "").strip():
                    decision = "escalate"
                elif human_review_override(ticket.get("text", ""), classification.get("intent", "unclear_request")):
                    decision = "escalate"
                elif classification["intent"] in MANDATORY_ESCALATION_INTENTS:
                    decision = "escalate"
                elif classification["route_prediction"] != "auto_respond":
                    decision = "escalate"
                elif classification["route_confidence"] < route_threshold:
                    decision = "escalate"
                elif classification.get("answerable_probability", 0.0) < answerability_threshold:
                    decision = "escalate"
                elif not sources:
                    decision = "escalate"
                else:
                    decision = "auto_respond"
                predictions.append(decision)

            actual = [str((raw.get("labels") or {}).get("expected_route", "escalate")) for raw in tickets]
            tp = sum(p == "auto_respond" and y == "auto_respond" for p, y in zip(predictions, actual))
            fp = sum(p == "auto_respond" and y != "auto_respond" for p, y in zip(predictions, actual))
            fn = sum(p != "auto_respond" and y == "auto_respond" for p, y in zip(predictions, actual))
            tn = sum(p != "auto_respond" and y != "auto_respond" for p, y in zip(predictions, actual))
            rows.append({
                "route_threshold": route_threshold,
                "answerability_threshold": answerability_threshold,
                "auto_responded": predictions.count("auto_respond"),
                "escalated": predictions.count("escalate"),
                "automation_rate_percent": round(100 * predictions.count("auto_respond") / len(predictions), 2) if predictions else 0,
                "auto_precision": round(tp / (tp + fp), 4) if tp + fp else 0.0,
                "auto_recall": round(tp / (tp + fn), 4) if tp + fn else 0.0,
                "accuracy": round((tp + tn) / len(predictions), 4) if predictions else 0.0,
                "false_auto_responses": fp,
            })
    return {"validation_file": input_path.name, "validation_ticket_count": len(tickets), "threshold_sweep": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DATA_DIR / "validation_tickets.json")
    parser.add_argument("--output", type=Path, default=Path("evaluation/results/threshold_sweep.json"))
    parser.add_argument("--route-thresholds", default="0.50,0.55,0.60,0.65,0.70")
    parser.add_argument("--answerability-thresholds", default="0.50,0.55,0.60,0.65")
    args = parser.parse_args()
    result = evaluate(args.input, [float(x) for x in args.route_thresholds.split(",")], [float(x) for x in args.answerability_thresholds.split(",")])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "candidates": len(result["threshold_sweep"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
