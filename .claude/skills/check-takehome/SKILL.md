---
name: check-takehome
description: Verify the take-home deliverables. Runs the Python script from a clean state, checks the three output CSVs against fixed acceptance values, and sanity-checks the SQLite database. Use after changing update_catalog.py or the SQL loader, or before committing or submitting.
allowed-tools: Bash(python *) Bash(.venv/Scripts/python *)
---

# Check take-home deliverables

1. Regenerate the Python outputs from scratch:
   `.venv/Scripts/python update_catalog.py` (fall back to `python update_catalog.py` if no venv).
2. Run the acceptance checker:
   `.venv/Scripts/python ${CLAUDE_SKILL_DIR}/scripts/check_outputs.py`
3. Report the checker's pass/fail table as-is.

Rules:
- The expected values live in `scripts/check_outputs.py`. Never edit them to make a check pass.
- If a check fails, explain the likely cause in the code before proposing a fix.
- SQL checks are skipped until `sql/nba.db` exists. That is not a failure.
