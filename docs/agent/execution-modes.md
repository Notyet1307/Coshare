# Execution Modes

Phase 1 supports three execution modes at the task-contract level.

## Direct Mode

Use Direct Mode for small, low-risk, clear tasks.

Typical examples:

- writing governance docs
- creating milestone templates
- adding small parser behavior
- updating tests and fixtures

## Subagent Mode

Use Subagent Mode when role separation matters.

Typical examples:

- independent review
- verifier-only execution
- failure scenario validation
- final dogfood acceptance

Subagent Mode in Phase 1 means role separation by prompt, session, or manual process. It does not require Multica or any platform integration.

## Borderline Mode

Use Borderline Mode when scope, risk, path boundaries, or required evidence are unclear.

Do not start implementation for Borderline tasks until uncertainty is resolved or explicitly recorded as a blocker.

## Role Boundaries

- Builder may change only files allowed by the task contract.
- Test Builder may change tests or explicitly allowed files.
- Verifier must not change code.
- Reviewer must not change code.
- Functional Tester should avoid implementation details when black-box testing is possible.
- Orchestrator cannot override hard gate rules.
