from __future__ import annotations
import json, math, statistics
from collections import defaultdict
from pathlib import Path
from typing import Any


def _prf(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    labels = sorted(set(y_true) | set(y_pred))
    per_class = {}
    for label in labels:
        tp = sum(a == label and b == label for a, b in zip(y_true, y_pred))
        fp = sum(a != label and b == label for a, b in zip(y_true, y_pred))
        fn = sum(a == label and b != label for a, b in zip(y_true, y_pred))
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_class[label] = {"precision": round(precision, 4), "recall": round(recall, 4), "f1": round(f1, 4), "support": sum(x == label for x in y_true)}
    accuracy = sum(a == b for a, b in zip(y_true, y_pred)) / len(y_true) if y_true else None
    return {"accuracy": round(accuracy, 4) if accuracy is not None else None, "per_class": per_class,
            "macro_f1": round(sum(v["f1"] for v in per_class.values()) / len(per_class), 4) if per_class else None}


def _calibration_summary(confidences: list[float], correct: list[bool], bins: int = 5) -> dict[str, Any]:
    """Expected calibration error for top-label confidence, with visible bin counts."""
    if not confidences or len(confidences) != len(correct):
        return {"expected_calibration_error": None, "bins": []}
    grouped: list[list[tuple[float, bool]]] = [[] for _ in range(bins)]
    for confidence, is_correct in zip(confidences, correct):
        value = max(0.0, min(1.0, float(confidence)))
        index = min(bins - 1, int(value * bins))
        grouped[index].append((value, bool(is_correct)))
    output = []
    ece = 0.0
    total = len(confidences)
    for index, group in enumerate(grouped):
        if not group:
            continue
        avg_confidence = sum(item[0] for item in group) / len(group)
        accuracy = sum(item[1] for item in group) / len(group)
        ece += len(group) / total * abs(avg_confidence - accuracy)
        output.append({
            "lower_bound": round(index / bins, 2),
            "upper_bound": round((index + 1) / bins, 2),
            "count": len(group),
            "mean_confidence": round(avg_confidence, 4),
            "accuracy": round(accuracy, 4),
        })
    return {"expected_calibration_error": round(ece, 4), "bins": output, "sample_size": total}


def build_metrics(results: list[dict[str, Any]], input_tickets: list[dict[str, Any]], run_started: str) -> dict[str, Any]:
    n = len(results)
    actions = [r.get("decision", "escalate") for r in results]
    latencies = [float(r.get("latency_ms", 0.0)) for r in results]
    ordered = sorted(latencies)
    p95 = ordered[min(len(ordered)-1, max(0, math.ceil(.95 * len(ordered))-1))] if ordered else 0.0
    route_true, route_pred, final_route_pred, intent_true, intent_pred, answerability_true, answerability_pred = [], [], [], [], [], [], []
    intent_confidences, intent_correct = [], []
    route_confidences, route_correct = [], []
    answerability_probabilities, answerability_true_labels = [], []
    retrieval_hits = retrieval_total = 0
    channel_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "auto_respond": 0, "escalate": 0, "guardrail_blocked": 0})
    group_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "auto_respond": 0})
    for raw, result in zip(input_tickets, results):
        labels = raw.get("labels") or {}
        if labels.get("expected_route"):
            expected_route = str(labels["expected_route"])
            route_true.append(expected_route)
            predicted_route = str(((result.get("alternatives") or {}).get("route") or [{}])[0].get("label", result.get("decision")))
            route_pred.append(predicted_route)
            final_route_pred.append(str(result.get("decision", "escalate")))
            route_confidences.append(float(result.get("confidence", 0.0)))
            route_correct.append(predicted_route == expected_route)
        if labels.get("intent"):
            intent_true.append(str(labels["intent"]))
            intent_pred.append(str(result.get("intent")))
            intent_confidences.append(float(result.get("intent_confidence", 0.0)))
            intent_correct.append(str(result.get("intent")) == str(labels["intent"]))
        if isinstance(labels.get("answerable_from_docs"), bool):
            answerability_true.append(str(labels["answerable_from_docs"]))
            answerability_pred.append(str(bool(result.get("answerability_prediction", False))))
            answerability_probabilities.append(float(result.get("answerable_probability", 0.5)))
            answerability_true_labels.append(bool(labels["answerable_from_docs"]))
        expected_docs = set(labels.get("expected_doc_ids") or [])
        if expected_docs:
            retrieval_total += 1
            got = {s.get("doc_id") for s in result.get("sources", [])}
            retrieval_hits += int(bool(expected_docs & got))
        ch = str(raw.get("channel", "unknown"))
        channel_stats[ch]["total"] += 1
        channel_stats[ch][result.get("decision", "escalate")] += 1 if result.get("decision") in {"auto_respond", "escalate"} else 0
        if result.get("guardrail", {}).get("passed") is False:
            channel_stats[ch]["guardrail_blocked"] += 1
        region = str(raw.get("customer_region", "unknown"))
        group_stats[region]["total"] += 1
        group_stats[region]["auto_respond"] += int(result.get("decision") == "auto_respond")
    auto = actions.count("auto_respond")
    escalated = actions.count("escalate")
    blocked = sum(bool(r.get("guardrail", {}).get("blocked")) for r in results)
    # Offline estimate only: an automated answer is not proof of resolution. Labelled FCR is reported separately.
    labelled_fcr = [bool((raw.get("history") or {}).get("first_contact_resolution")) for raw in input_tickets if isinstance(raw.get("history"), dict) and "first_contact_resolution" in raw["history"]]
    labelled_escalation = [bool((raw.get("labels") or {}).get("expected_route") == "escalate") for raw in input_tickets if (raw.get("labels") or {}).get("expected_route")]
    historical_resolution_minutes = [float((raw.get("history") or {}).get("resolution_time_minutes")) for raw in input_tickets if isinstance(raw.get("history"), dict) and isinstance((raw.get("history") or {}).get("resolution_time_minutes"), (int, float))]
    historical_csat = [float((raw.get("history") or {}).get("csat_rating")) for raw in input_tickets if isinstance(raw.get("history"), dict) and isinstance((raw.get("history") or {}).get("csat_rating"), (int, float))]
    log_failures = sum(bool(r.get("logging_error")) for r in results)
    return {
        "run_started_utc": run_started,
        "tickets_processed": n,
        "tickets_auto_responded": auto,
        "tickets_escalated": escalated,
        "guardrail_blocked": blocked,
        "automation_rate_percent": round(100 * auto / n, 2) if n else 0.0,
        "escalation_rate_percent": round(100 * escalated / n, 2) if n else 0.0,
        "first_contact_resolution_proxy_percent": round(100 * auto / n, 2) if n else 0.0,
        "labelled_first_contact_resolution_percent": round(100 * sum(labelled_fcr) / len(labelled_fcr), 2) if labelled_fcr else None,
        "historical_resolution_time_minutes": {"mean": round(statistics.mean(historical_resolution_minutes), 2) if historical_resolution_minutes else None, "median": round(statistics.median(historical_resolution_minutes), 2) if historical_resolution_minutes else None, "sample_size": len(historical_resolution_minutes)},
        "historical_csat_average": round(statistics.mean(historical_csat), 2) if historical_csat else None,
        "historical_csat_sample_size": len(historical_csat),
        "labelled_expected_escalation_rate_percent": round(100 * sum(labelled_escalation) / len(labelled_escalation), 2) if labelled_escalation else None,
        "response_latency_ms": {"mean": round(statistics.mean(latencies), 2) if latencies else 0.0, "median": round(statistics.median(latencies), 2) if latencies else 0.0, "p95": round(p95, 2)},
        "intent_classification": _prf(intent_true, intent_pred),
        "answerability_classification": _prf(answerability_true, answerability_pred),
        "confidence_calibration": {"intent": _calibration_summary(intent_confidences, intent_correct), "route": _calibration_summary(route_confidences, route_correct), "answerability": _calibration_summary(answerability_probabilities, answerability_true_labels)},
        "routing_classification": _prf(route_true, route_pred),
        "final_decision_classification": _prf(route_true, final_route_pred),
        "retrieval_hit_rate_percent": round(100 * retrieval_hits / retrieval_total, 2) if retrieval_total else None,
        "retrieval_evaluated_tickets": retrieval_total,
        "channel_breakdown": dict(channel_stats),
        "customer_region_automation_breakdown": {k: {**v, "automation_rate_percent": round(100*v["auto_respond"]/v["total"],2) if v["total"] else 0.0} for k,v in group_stats.items()},
        "decisions_logged": n - log_failures,
        "decision_log_failures": log_failures,
        "private_data_detections": sum(bool(r.get("guardrail", {}).get("private_data_types")) for r in results),
        "notes": ["Auto-response is a proxy for potential first-contact resolution, not observed resolution.", "Historical resolution-time and CSAT values describe the supplied labelled records, not this pipeline run.", "Latency includes local processing and any configured provider call; this run's figures are environment-specific.", "Metrics using expected labels are computed only when labels are present in the input."]
    }


def write_metrics(metrics: dict[str, Any], output_path: Path) -> Path:
    path = output_path.with_name("metrics.json")
    path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    return path
