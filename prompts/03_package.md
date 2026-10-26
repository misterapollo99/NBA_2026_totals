# Prompt 3: Package for submission

Run after both parts pass /check-takehome.

---

<instructions>
1. Run /code-review on the full diff and fix anything it flags that is a real issue. Tell me what you changed and what you chose not to change.
2. Create README.md: what's in the folder, how to run each part (exact PowerShell commands from a fresh clone), engine and dependency versions, and one "Assumptions and decisions" section covering both parts. Keep it under one screen. Plain, professional tone, no em dashes, no marketing language.
3. Run `ruff check .` and `ruff format --check .` and fix any issues.
4. Delete the files in output/ and sql/nba.db, rerun both parts from scratch using only the README commands, then run /check-takehome to prove the README is reproducible.
5. Commit with a clear message.
</instructions>
