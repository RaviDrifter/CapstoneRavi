# Clean-checkout checklist

- [ ] Extract or clone the repository into an empty directory.
- [ ] Use Python 3.11 (supported range in `pyproject.toml`: Python 3.10–3.12).
- [ ] Create and activate a virtual environment.
- [ ] Install the pinned dependencies from `requirements.txt`.
- [ ] Copy `.env.example` to `.env`; leave the API key blank for offline tests.
- [ ] Run `python -m pytest tests/ -v`.
- [ ] Run the validation command from the README.
- [ ] Confirm 80 input records yield 80 result records.
- [ ] Confirm `metrics.json` is produced automatically.
- [ ] Confirm successful decision-log writes equal processed records.
- [ ] Run a prompt-injection test and confirm the response is blocked.
- [ ] Simulate provider timeout and confirm the batch continues using the evidence template.
- [ ] Search the repository for real API keys, tokens, passwords, and private customer data.
- [ ] Do not run threshold tuning against the hidden evaluation set.
