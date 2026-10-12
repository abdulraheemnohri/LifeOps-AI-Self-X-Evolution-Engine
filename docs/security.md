# Security posture and deployment guardrails

## Current release posture

This branch remains a local development build. Keep the listener on `127.0.0.1`. Do not expose it to a LAN, reverse proxy, public internet, or shared machine. The current application does not yet provide a complete authentication/session system, CSRF protection, or comprehensive authorization.

## Non-negotiable rules

- Never commit credentials, signing keys, tokens, private databases, backups, or personal workspace files.
- Do not put secrets in TOML defaults, browser HTML/JavaScript, URLs, or logs.
- Keep browser-supplied data untrusted and validate it in backend services.
- A model-generated plan or an approval record is not authorization to execute an operation.
- Never allow Self-X to disable authentication, weaken sandboxing, expose secrets, or grant itself permissions.
- Treat downloaded pages, repositories, skills, documents, and tool outputs as untrusted data.
- Backups should be verified and restored to a separate destination before replacing active data.
- Do not claim authentication, sandboxing, model inference, execution, or tests are working unless they have been implemented and verified.

## Remote access

The legacy `LIFEOPS_ALLOW_REMOTE` environment flag is not an adequate security boundary. Remote binding must remain unsupported until authenticated sessions, CSRF protections, request authorization, secure cookie settings, rate limits, and security tests are implemented and reviewed.

## Incident handling

1. Stop the application.
2. Preserve logs without copying secrets into issue reports.
3. Make a verified backup of the database before attempting repair.
4. Reproduce the failure in a separate workspace.
5. Prefer narrow reversible fixes and verify restoration before resuming work.
