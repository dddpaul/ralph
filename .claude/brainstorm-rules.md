## Save Design Conclusions (before Phase 4)

At the end of Phase 3 (after convergence, before presenting Phase 4 options), propose saving the design conclusions to `design/<name>-brainstorm.md` where `<name>` is a kebab-case slug shared with the eventual PRD (e.g., `design/auth-token-rotation-brainstorm.md`).

The file must follow this structure:

```markdown
# <Title>

## Architecture decision
What was chosen, briefly.

## Components / flows
- Bullet list of components, services, or data flows involved.

## Scope cuts
- What we explicitly excluded and why.

## Open questions
- Anything deferred for later resolution.

## Hand-off
Next: `ralph-prd` to formalize as PRD, then `ralph-backlog` to generate tasks.
```

If the user approves, write the file and confirm. If declined, skip and proceed to Phase 4.

This rule supplements (does not replace) any user-global Phase 4 rules — both apply.

---

## Phase 4 Override

In Phase 4 (Next Steps), the first option must always be:

- **Create backlog task(s)** — Invoke the `ralph-task` skill with the brainstorm context (selected approach, design decisions, acceptance criteria, testing strategy) sufficient for autonomous execution in a Ralph loop without human guidance. If the scope is PRD-shaped (≥3 user stories, multiple lanes), `ralph-task`'s pre-check will redirect to `ralph-prd` → `ralph-backlog`.

The remaining options (Write plan, Plan mode, Start now) follow after.
