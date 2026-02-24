# Task Completion Checklist

## After Implementation

1. **Run all tests**:
   ```bash
   python3 -m pytest tests/ -q
   ```
   All ~1706 tests must pass.

2. **Document updates** (if applicable):
   - `intent-routing.md` — New keywords/intents
   - Relevant `SKILL.md` — Changed skill features/output
   - `CLAUDE.md` — Architecture/module changes
   - `rules/portfolio.md` or `rules/screening.md` — Domain-specific rule changes
   - `README.md` — User-facing feature descriptions

3. **Judgment criteria**:
   - New feature → update intent-routing + SKILL.md + CLAUDE.md + README.md
   - Enhancement → update SKILL.md + relevant rules
   - Bug fix only → no doc update needed (unless behavior changed)

## Git Workflow
- Branch: `feature/kik-{NNN}-{short-desc}`
- Worktree: `~/stock-skills-kik{NNN}`
- Merge: `git merge --no-ff` to main
- Never edit main branch directly

## Pre-commit Hook
- `scripts/hooks/pre-commit` blocks commits if `src/` changed but docs not updated
- Bypass with `--no-verify` if needed
