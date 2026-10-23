import json
from pathlib import Path
from src.cli import run

ROOT = Path(__file__).resolve().parents[1]

def test_cli_run_writes_results_and_metrics(tmp_path):
    inp = tmp_path / "tickets.json"
    out = tmp_path / "results.json"
    inp.write_text(json.dumps([
        {"ticket_id": "A", "channel": "email", "subject": "Question", "body": "How do I configure the API endpoint?"},
        {"ticket_id": "B", "channel": "chat", "subject": "Compliance", "body": "Please provide an official compliance certification statement."},
    ]), encoding="utf-8")
    metrics = run(inp, out)
    results = json.loads(out.read_text(encoding="utf-8"))
    assert len(results) == 2
    assert [x["ticket_id"] for x in results] == ["A", "B"]
    assert (tmp_path / "metrics.json").exists()
    assert metrics["decisions_logged"] == 2
    assert metrics["tickets_processed"] == 2
