# Architecture and Phase 1 acceptance checklist

LifeOps is a local-first modular monolith. Browser routes and future workers must call the same validated service layer. SQLAlchemy models persist to SQLite by default under `data/lifeops.db`; set `LIFEOPS_DATA_DIR` or `LIFEOPS_DATABASE_URL` to change the location.

## Trust boundaries

- Browser inputs are untrusted and validated by service functions.
- SQLite stores operational records and audit events.
- The model runtime is currently unconfigured. Model output must never authorize tools or mutate policy.
- The web server binds to loopback by default. Remote binding is blocked unless explicitly opted into; authentication is not yet implemented, so remote exposure is not suitable for production.
- Research content, imported skills, and documents must be treated as untrusted when those modules are introduced.

## Phase 1 acceptance checklist

- [x] Establish package entry point and local SQLite persistence.
- [x] Implement task creation, listing, completion, and audit records.
- [x] Implement note creation and listing.
- [x] Provide responsive browser pages for overview, tasks, notes, diagnostics, and settings status.
- [x] Provide a machine-readable health endpoint.
- [x] Add deterministic service tests.
- [ ] Authentication, CSRF protection, and user/session isolation.
- [ ] Versioned database migrations and backup/restore verification.
- [ ] Browser-level end-to-end tests on Windows and Linux.
- [ ] Model adapter, persistent job queue, policy engine, and approval lifecycle.

Checked items describe code added in this branch, not tests already executed in a deployment environment. Run `pytest` locally to verify the current checkout.
