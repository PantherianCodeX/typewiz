# Draft logs (mirrors)

This folder holds *mirrors* of the “Draft log” section from each rewritten ADR/spec.

## Why this exists
- Provides stable audit trail and review context without needing to open each in-progress document.
- Enables diffs, review, and enforcement of the “no untracked changes” rule.

## Rules
- Each rewritten doc must have a corresponding mirror file:
  - Example: `docs/_internal/adr/0003-policy-boundaries.md` → `docs/_internal/draft_logs/ADR-0003.md`
- The mirrored log must remain consistent with the doc’s internal draft log section.
- If drift is detected, treat it as a blocker and record a Q-entry in:
  - `docs/_internal/s11r2/registers/open_questions.md`

## Suggested naming
- ADRs: `ADR-####.md`
- Reference specs: `REF-<name>.md`
- CLI contract docs: `CLI-<name>.md`

Use `docs/_internal/s11r2/templates/draft-log-template.md` as the baseline.
