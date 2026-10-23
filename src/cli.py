from __future__ import annotations
import argparse, json, logging, os, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .config import LOG_LEVEL
from .metrics import build_metrics, write_metrics
from .pipeline import SupportPipeline

logging.basicConfig(level=getattr(logging, LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")

def _load_input(path: Path) -> list[Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and isinstance(value.get("tickets"), list):
        return value["tickets"]
    raise ValueError("Input JSON must be a list of ticket objects or an object with a 'tickets' list.")

def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(value, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_name, path)
    except Exception:
        try: os.unlink(tmp_name)
        except OSError: pass
        raise

def run(input_path: str | Path, output_path: str | Path, threshold: float | None = None) -> dict[str, Any]:
    input_file, output_file = Path(input_path).resolve(), Path(output_path).resolve()
    run_started = datetime.now(timezone.utc).isoformat()
    tickets = _load_input(input_file)
    pipeline = SupportPipeline(confidence_threshold=threshold) if threshold is not None else SupportPipeline()
    results = []
    for i, ticket in enumerate(tickets):
        if not isinstance(ticket, dict):
            ticket = {"ticket_id": f"INVALID-{i + 1}", "channel": "unknown", "body": ""}
        results.append(pipeline.process(ticket, i))
        if (i + 1) % 25 == 0:
            logging.info("Processed %s/%s tickets", i + 1, len(tickets))
    _atomic_json(output_file, results)
    metrics = build_metrics(results, [x if isinstance(x, dict) else {} for x in tickets], run_started)
    metrics["input_file"] = input_file.name
    metrics["output_file"] = output_file.name
    metrics["system_version"] = "1.0.0"
    metrics_path = write_metrics(metrics, output_file)
    logging.info("Completed %d tickets. Output: %s; metrics: %s", len(results), output_file, metrics_path)
    return metrics

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Process CloudServe support tickets unattended.")
    parser.add_argument("--input_path", "--input", dest="input_path", required=True, help="Path to input JSON file")
    parser.add_argument("--output_path", "--output", dest="output_path", required=True, help="Path for results JSON file")
    parser.add_argument("--confidence-threshold", type=float, default=None, help="Optional routing confidence threshold override")
    args = parser.parse_args(argv)
    metrics = run(args.input_path, args.output_path, args.confidence_threshold)
    print(json.dumps({"tickets_processed": metrics["tickets_processed"], "auto_responded": metrics["tickets_auto_responded"], "escalated": metrics["tickets_escalated"], "metrics_file": str(Path(args.output_path).resolve().with_name("metrics.json"))}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
