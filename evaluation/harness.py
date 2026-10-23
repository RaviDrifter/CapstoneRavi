from __future__ import annotations
import argparse, json
from pathlib import Path
from src.cli import run

def main(argv=None):
    parser = argparse.ArgumentParser(description="Unattended evaluation harness for CloudServe AI Support")
    parser.add_argument("--input", "--input_path", dest="input_path", required=True)
    parser.add_argument("--output", "--output_path", dest="output_path", required=True, help="Output JSON file or directory")
    args = parser.parse_args(argv)
    out = Path(args.output_path)
    if out.exists() and out.is_dir() or (not out.suffix):
        out.mkdir(parents=True, exist_ok=True)
        out = out / "results.json"
    metrics = run(args.input_path, out)
    print(json.dumps({"output": str(out.resolve()), "metrics": str(out.resolve().with_name("metrics.json")), "processed": metrics["tickets_processed"], "auto_responded": metrics["tickets_auto_responded"], "escalated": metrics["tickets_escalated"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
