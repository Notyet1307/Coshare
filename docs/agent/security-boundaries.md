# Security Boundaries

Phase 1 is local governance only.

Do not implement external integrations, model API calls, deployment automation, or VPN/internal network automation.

## Forbidden Paths

Never modify these paths unless the active task contract explicitly allows it:

- `.env`
- `.env.*`
- `secrets/**`
- `infra/prod/**`

## Secrets

Do not read, print, copy, or write secrets into:

- docs
- evidence files
- closeout files
- logs
- tests
- fixtures
- comments

Do not use production credentials.

Do not access production systems.

Do not assume VPN or internal network access unless explicitly allowed by the active task.

## Bridge Boundary

`tools/agent-bridge` is a local governance CLI.

It must not:

- call Codex
- call DeepSeek
- call model APIs
- create GitHub Issues
- create GitLab Issues
- create Multica Issues
- merge code
- push branches
- run autonomous loops
- modify production systems
