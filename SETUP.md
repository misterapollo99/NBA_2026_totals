# Setup and Demo Guide

Personal prep notes. Delete or move this file before submitting.

## Tonight (about 30 minutes)

1. **Run the setup script** from this folder in PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\setup.ps1
   ```
   It checks prerequisites, builds `.venv`, installs pandas, ruff, and pyright, pins versions, smoke-tests the checker, and makes the first git commit.

2. **Open in VS Code:** run `code .` and click **Install** on the recommended-extensions prompt (Claude Code, Python, Ruff, Rainbow CSV, SQLite Viewer, GitLens).

3. **Start Claude Code** in the VS Code terminal:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   claude
   ```
   - Accept the workspace trust prompt and the prompt to install the two project plugins.
   - If the plugins don't prompt, install them by hand:
     ```
     /plugin install pyright-lsp@claude-plugins-official
     /plugin install security-guidance@claude-plugins-official
     ```
   - Run `/doctor` and fix anything it flags.
   - Run `/skills` and confirm `check-takehome` is listed.

4. **Test the hook:** ask Claude to "create scratch.py with a badly formatted function." It should come back formatted by ruff. Then delete `scratch.py`.

5. **Dry run:** follow `prompts/01_python.md` end to end.

## What each piece is for

| Piece | Where | Why |
|---|---|---|
| Project memory | `CLAUDE.md` | Conventions and guardrails Claude reads every session |
| Permissions | `.claude/settings.json` | Pre-approves safe commands, blocks `git push` and destructive deletes |
| Format hook | `.claude/hooks/ruff_format.py` | Every `.py` edit is auto-formatted, so style is enforced, not requested |
| Custom skill | `.claude/skills/check-takehome/` | Acceptance tests written before any code; Claude can't move the goalposts |
| pyright-lsp plugin | official marketplace | Claude sees type errors right after its own edits |
| security-guidance plugin | official marketplace | Checks edits and commits for risky patterns |
| Built-in skills | `/doctor`, `/code-review`, plan mode | Setup health, self-review before submitting, plan-before-code |
| Repo hygiene | venv, `requirements.lock.txt`, `pyproject.toml`, git | Reproducible environment and a readable history |

## Demo walkthrough (about 5 minutes)

1. **Environment:** VS Code, project venv, pinned dependencies, ruff configured in `pyproject.toml`.
2. **Structure:** `data/`, `output/`, `sql/`, `prompts/`, and the git log.
3. **`CLAUDE.md`:** "This is how I scope the agent: conventions, guardrails, and a plan-before-code rule."
4. **`.claude/`:** permissions, the format hook, and the custom `check-takehome` skill.
5. **Workflow:** plan mode, review the ambiguities, approve, execute, then `/check-takehome`.
6. **Validation:** open an output CSV in Rainbow CSV, query `nba.db` in SQLite Viewer, run the script live.

**The message to land:** the tool accelerates me; I own the decisions and the validation.

## Likely questions

- **"How do you know the AI's output is right?"** I wrote the expected values by hand before any code existed, encoded them in a skill, and told Claude it can't edit them. Then I inspect outputs myself.
- **"What ambiguity did you hit?"** Remove-before-canonicalize for colors, traded-player rows in the NBA data, and league FG% as SUM/SUM rather than an average of percentages.
- **"Why SQLite?"** No server, portable, and right-sized for one CSV. Postgres if this needed concurrency or scale.
- **"Why so few plugins?"** Every skill costs context on every turn. Each piece here has a specific job.
- **"What changes in production?"** Schema validation on inputs, pytest in CI, and a review queue for unmapped colors instead of a silent title-case fallback.
