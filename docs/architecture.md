# Architecture and implementation status

LifeOps is a local-first modular monolith. Browser routes and future workers should call the same validated service layer. SQLAlchemy persists operational records to SQLite by default in `data/lifeops.db`.

## Trust boundaries

- Browser input is untrusted and must be validated server-side.
- SQLite stores tasks, notes, projects, memories, approvals, agent-run requests, and audit events.
- Model inference is not configured in this release. Requests submitted to the run service are persisted as `needs_input`; no fake execution is reported.
- The deterministic policy engine never accepts model output as authorization. Destructive/system-security actions are hard blocked or approval gated.
- Research pages, documents, imported skills, and external tool outputs must be treated as untrusted.
- The web server binds to loopback by default. Authentication and CSRF protection remain release blockers for remote exposure.

## Current milestone

Implemented: task create/list/update/delete/complete services; project creation/listing; note create/list/search/update/delete services; searchable user memory with categories; single-decision approval records; deterministic action policy; persistent agent request records that explicitly report missing model runtime; audit records; local install scripts and CI.

Still not implemented: authentication/session isolation, CSRF middleware, Alembic revisions, persistent worker execution, actual model adapters, integrations, full calendar/recurrence, file sandbox, skill sandbox/publishing, isolated self-repair, cryptographic backup encryption, and browser E2E tests.

## Security decisions

The policy engine returns `ALLOW`, `ASK`, or `BLOCK`. Approval records are an audit/decision mechanism only; the application must not execute the underlying action unless a separately implemented executor verifies the policy decision and approved action identity. Remote binding is not safe until authentication and CSRF protections ship.

## Acceptance checklist

- [x] Local SQLite persistence and health route
- [x] Tasks and notes through browser UI
- [x] Service validation and audit events
- [x] Project, memory, approval and agent-run persistence services
- [x] Deterministic policy decision unit tests
- [ ] Authentication, sessions, CSRF, and authorization
- [ ] Alembic migrations and verified restore tests
- [ ] Real model adapter with capability detection and cancellation
- [ ] Durable worker queue, step logs, retry and recovery
- [ ] Skills lifecycle and isolated repair/evaluation workflows
- [ ] Browser-level tests and Windows/Linux CI verification
