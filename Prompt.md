### LifeOps AI + Self-X Evolution Engine

### Complete A-to-Z Master Project Prompt

This specification defines a complete, self-hosted personal AI platform combining LifeOps productivity automation with the Self-X self-evolution engine, inspired by the general capabilities of Hermes Agent.

The project is designed as a real application—not just a chatbot or a static dashboard. It covers the architecture, every major feature, functions, web pages, settings, security rules, database, APIs, autonomous workflows, testing, installation, and deployment.

![AI Personal Assistant | Automate Your Life with KeepClaw](https://images.openai.com/static-rsc-4/90HGl33SdzvpXaBT6-G26mwiTxh2Rw6N4JcRb1wzdyG8c0s9X7cpkiO3ikgpv8IteoSkRMyu1IbHmNXuTj7vCCjm6bsh4RBnBafyyUjrXaM4Qi8AWioCunejzTGygcafVxNj_t5AOaAjIA7uZJZM_S0eSpPVQZuG35RkRTIRwQ9HYh-m0lzqoG7iFiEhvdY6?purpose=fullsize)

![Build a Hermes AI Student Companion & Mission Control Dashboard | Komputer Mechanic](https://images.openai.com/static-rsc-4/hzvM8dhTgD5tqViMVxy7ZYBddAfmP7eJIlLO2kfYnamGDwv_8vHYlCCbWodHPJTA_0ogOkS2BogjGI3aUtWFm1rEsXsVkjkGKP5nSCOwVSIvBahA8Gg4o94YSV8Gf7X6uWHZD1l3imikgB0SjIMM9mEIW4zJafvsne_kmjAmY2VeE-WhpmKuPMMhmDybYFL2?purpose=fullsize)

![LifeGraph | Devpost](https://images.openai.com/static-rsc-4/xDTbWt8IkthKFOHfUrSzJW-n6HQeWCnlOB-Csle5NNuQcBi4joqsDrZqsPGcCKCC3CYoQIs4-oTVnb_Rx9a5aaOKKRyIidDl5deUNEq5A6u-9TY-oSycy0U7YH3QhdF17L28tEhdIiXCBXHAUvERz5y4I67iIqRTPa8BDGSa9vhu3uX7Y9FoG77YLEHFPu0S?purpose=fullsize)

Web UI only

Browser-based control center for every user-facing operation.

Self-X evolution

Diagnostics, research, evaluation, skill learning, and recovery.

Local-first

Persistent SQLite storage, backups, and offline-capable core features.

Controlled autonomy

Policy enforcement, approvals, sandboxing, checkpoints, and audit logs.

### 1\. Master project definition

# PROJECT MASTER PROMPT: LifeOps AI + Self-X Evolution Engine

## Project mission

Build a complete, production-oriented, self-hosted personal AI operating platform named **LifeOps AI + Self-X Evolution Engine**.

LifeOps AI is the user-facing personal productivity and automation assistant. Self-X is the integrated self-diagnostics, self-research, self-evaluation, skill-learning, recovery, and controlled self-improvement subsystem.

The application must be fully usable through a modern browser-based Web UI. Do not require users to operate a CLI or TUI for normal application tasks. Administrative terminal commands may be provided for installation, upgrades, backup recovery, and troubleshooting.

The repository must contain actual working source code, backend logic, database migrations, templates, frontend assets, tests, documentation, configuration examples, and installation scripts.

Do not deliver a mockup, empty page, placeholder implementation, fake integration, or buttons that do nothing.

## Non-negotiable principles

1. Local-first and self-hosted by default.
2. No mandatory Firebase, commercial AI API, cloud database, or Docker.
3. Offline-capable operation for supported local features.
4. Browser-based Web UI as the sole primary presentation layer.
5. Persistent, searchable, editable, exportable, and recoverable memory.
6. Self-learning through experience, research, skills, evaluations, and tested workflow improvements.
7. Strict separation between model-generated proposals and trusted policy enforcement.
8. Human approval for sensitive or irreversible operations.
9. Real task execution with visible status, cancellation, logs, and error handling.
10. Native installation and operation on supported Windows and Linux environments.
11. Modular inference adapters, tool integrations, and extensible skills.
12. No false claims that a task, test, integration, or self-improvement succeeded.
13. Complete documentation, automated tests, and reproducible installation.
14. A user-controlled donation mechanism may be included; donations must never be required to use core features.

## Required initial technology stack

- Python 3.12 or newer, using a version supported by all selected dependencies.
- FastHTML and HTMX for server-rendered interactive Web UI.
- HTML, CSS, and JavaScript for frontend components and browser interactions.
- A single consistent asynchronous web application framework; avoid duplicating routing systems unnecessarily.
- Pydantic for configuration and data validation.
- SQLAlchemy 2.x and SQLite for persistent application data.
- Alembic or an equivalent migration system.
- asyncio and a persistent database-backed job queue for background execution.
- WebSockets or server-sent events for real-time job updates.
- pytest for unit, integration, and end-to-end tests.
- A modular model adapter interface supporting LiteRT-LM CLI and optional additional compatible runtimes.

Do not assume an undocumented model CLI command exists. Detect and validate the installed runtime, supported commands, version, model compatibility, and streaming/cancellation capabilities before enabling corresponding functions.

## Product architecture

Separate the system into:

1. Web presentation layer.
2. Application and API layer.
3. LifeOps task and productivity services.
4. Agent planning and execution orchestrator.
5. Self-X evolution engine.
6. Model adapter and inference layer.
7. Tool registry and integration adapters.
8. Security and permission enforcement layer.
9. Persistent storage and memory services.
10. Scheduler and background worker services.
11. Observability, backup, and recovery services.

All significant operations must use validated service interfaces. The model must not directly modify the database, permission policies, secrets, or operating-system security configuration.

## Core product outcome

A user must be able to open the Web UI, manage personal work, ask the assistant to complete a task, inspect the execution plan, approve sensitive actions, view results, store useful memories, create reusable skills, inspect Self-X health, and evaluate or roll back proposed improvements—all from one integrated application.

### 2\. Core architecture and execution lifecycle

Web UI

Dashboard · Assistant · Tasks · Self-X · Settings

Application API and authentication

Validation · Sessions · Request limits · Audit correlation

Policy and orchestration

Planner · Approval gate · Executor · Scheduler · Worker manager

LifeOps services

Tasks, files, reminders, research

Self-X services

Learning, diagnostics, evaluation, repair

Model adapters

Inference and structured outputs

Tools and integrations

Sandboxed, permission-checked execution

Persistent data and recovery

SQLite · Job state · Memory · Skills · Audit · Backups

### Mandatory task lifecycle

Every autonomous task must support these states:

`CREATED → PLANNING → AWAITING_APPROVAL → QUEUED → RUNNING → VERIFYING → SUCCEEDED`

Alternative terminal or paused states:

`FAILED`, `CANCELLED`, `PAUSED`, `TIMED_OUT`, `NEEDS_INPUT`.

Not every task needs approval. Low-risk tasks can proceed under a pre-authorized policy. Sensitive actions must stop at the approval gate until authorization is granted.

Every task must store its request, plan, tool calls, approvals, outputs, errors, timestamps, and verification evidence.

### 3\. Complete Web UI specification

The Web UI must use a consistent application shell, persistent navigation, search, notification center, task status indicators, accessible forms, confirmation dialogs, and responsive layouts.

### 3.1 Main navigation

| Page                   | Required functionality                                           |
| ---------------------- | ---------------------------------------------------------------- |
| Dashboard              | Overview, quick actions, recent tasks, reminders, system health  |
| AI Assistant           | Chat, plans, tools, execution, approvals, attachments            |
| Tasks & Projects       | CRUD operations, dependencies, priorities, due dates             |
| Calendar & Routines    | Events, recurring tasks, daily planning, reminders               |
| Notes & Knowledge      | Notes, tags, links, document indexing                            |
| Memory Explorer        | Memory search, editing, provenance, revisions, deletion          |
| Research Center        | Research jobs, sources, reports, saved findings                  |
| Skills Studio          | Skill authoring, validation, versions, tests, enable/disable     |
| Self-X Control Center  | Identity, diagnostics, goals, evaluations, improvement proposals |
| Automation & Scheduler | Triggers, workflows, schedules, run history                      |
| Worker Monitor         | Active jobs, queues, resource use, failures, cancellation        |
| Files & Documents      | Local file indexing, previews, supported document extraction     |
| Tools & Integrations   | Tool registry, permissions, connection health                    |
| Model Manager          | Runtime detection, models, inference settings, health            |
| Security & Approvals   | Pending approvals, policies, audit events                        |
| Analytics & Reports    | Productivity trends, agent success rates, evaluations            |
| Backup & Recovery      | Backups, restore, export, checkpoints                            |
| Notifications          | Reminders, failures, approvals, scheduled reports                |
| Settings               | All application preferences and system configuration             |
| Help & About           | Documentation, troubleshooting, version, licenses, donations     |

### 3.2 Shared UI components

Implement reusable components rather than creating each page independently:

* Application sidebar with collapsible navigation.

* Top bar with global search, connection status, notifications, and profile menu.

* Breadcrumbs and contextual actions.

* Data tables with search, filtering, sorting, and pagination.

* Create/edit forms with validation and unsaved-change protection.

* Status badges for jobs, approvals, integrations, and model health.

* Confirmation dialogs for destructive operations.

* Real-time progress indicators and event timelines.

* Log viewer with severity filters and redaction.

* Empty states, loading states, retry controls, and error messages.

* Keyboard-accessible controls and visible focus indicators.

* Responsive layouts for desktop, tablet, and mobile browsers.

* Light/dark theme options, with dark mode as the default.

* Import/export dialogs and reusable backup status indicators.

Every visible control must have a real action, a defined disabled state, or a clear explanation of why it is unavailable.

### 4\. LifeOps AI — feature and function specification

![Project Management System - ProjectFlow Console - Motiff AI](https://images.openai.com/static-rsc-4/7nNauRkkJlgcjFcGQgiotxw74JyDwoAapQ0AfqAAz5_W4zj-y2c2XwD76nBVqHyY5Vb26LUZM9qFjq6SRrBzdJxGfB_kVrNQt_x1-j9IrBzQI_6D40p2VD6Vi8Te_vbXlwWztqhcCSdOgrQZTDEk58EVCD1Lu9QHljGDz6RZDhAPKgZeJp4UU1ugxaTVml-Y?purpose=fullsize)

4.1 Task and project management

* Create, read, update, archive, and delete tasks.

* Assign priorities, due dates, categories, tags, and dependencies.

* Support subtasks, checklists, recurring tasks, and completion notes.

* Link tasks to projects, documents, memories, and agent runs.

* Detect overdue tasks and propose schedule adjustments.

* Preserve a history of task changes and completed work.

![Calendar Dark Mode - SquareUi by Rabii Mhamdi on Dribbble](https://images.openai.com/static-rsc-4/rhLq0_ELzI_kIuJ7vKmpMKEcaQ5xhCxsX8nQPdaKpKU1wx6Hue70RsJZYGSque3ns5-ua-jcEebLwlsvhQAc7Dl8-bN_5G-gcukxnnmHt-m1n4YIkheRviTp6pgo0Z8BgCm5PF6EVO2LHwZsH9HUQeTNFTWj28okYqE1zOPCKxPmctlnI7EKeDqKXIkoVNgv?purpose=fullsize)

4.2 Calendar, reminders, and routines

* Daily, weekly, monthly, and agenda views.

* One-time and recurring reminders.

* Time-zone-aware events and daylight-saving handling.

* Morning briefings, end-of-day summaries, and weekly reviews.

* Snooze, dismiss, reschedule, and mark-complete actions.

* Optional email or messaging notifications through configured integrations.

![2025 Obsidian Report Card](https://images.openai.com/static-rsc-4/yYYhqvjT3mIS0yPBTQsoM5rCq47k_pq6MOYn_PRptAUUTaNs8TP_r9VFr_p1jRShMJbkaXIQY4ANcXzYG5wmu9bWLkKBZAFIHaeoPtkafkJfhRmuj0oHmN8xgRuWNwe1sJ3zfZKskI6LrazRQl9t_b9Q_RTgufX5v6G-FRrmGS9EYYbPW7VrMXfZ-NEWhGuj?purpose=fullsize)

4.3 Notes, files, and knowledge

* Create rich-text or Markdown notes with tags and backlinks.

* Index user-selected directories and supported documents.

* Search document contents and extract summaries and action items.

* Track file hashes, source locations, indexing errors, and modification times.

* Support incremental indexing, exclusions, and re-indexing.

* Keep original documents unchanged unless the user authorizes edits.

![Tools & Permissions - Backend.AI GO](https://images.openai.com/static-rsc-4/BUL9QtUU8ZiknBJRwcM1r1oI5-SpRq03okafcHFkgKxoXkZFAvIKmmYNIrMth99Ogj4j7rzhSF4CKKjq-DHsr6P1kkla1QvvuI010JR4O7e7yzb1In4QUyEyGr2eqagkQYHiYf31PJopLZqI-gsIVPfyqIMfUof0i5-atvp-cDB1NA-YEwyZrsE5adeTbXG6?purpose=fullsize)

4.4 AI personal assistant

* Understand requests and ask clarifying questions when necessary.

* Convert objectives into structured plans and executable steps.

* Select tools based on capabilities, permissions, and task context.

* Show plans, progress, tool outputs, and final results.

* Support cancellation, retry, resume, and human handoff.

* Store user-approved memories and generate task summaries.

### 4.5 Daily planning engine

The daily planning engine must:

* Collect incomplete tasks, deadlines, reminders, and calendar events.

* Apply the user's working hours, preferred focus periods, and priorities.

* Identify scheduling conflicts and unrealistic workloads.

* Propose an ordered daily plan with estimated durations.

* Explain why each item is prioritized.

* Allow the user to accept, edit, or reject the plan.

* Track actual completion against the plan.

* Use the resulting performance data to suggest better future schedules.

Do not silently move existing calendar appointments or send notifications to other people.

### 4.6 Additional LifeOps modules

* Document assistant: extract text and action items from supported formats.

* Research assistant: browse configured sources, gather evidence, compare findings, and produce cited reports.

* Personal knowledge search: search notes, memories, task histories, and indexed documents.

* Workflow automation: trigger an approved series of actions when an event occurs.

* Personal analytics: show completion trends, overdue tasks, workload, and routine consistency.

* Notification center: consolidate reminders, failures, approvals, and important events.

* Optional integrations: calendar providers, email, messaging, and webhooks, each disabled until configured.

### 5\. Self-X Evolution Engine — detailed module specification

### 5.1 Self-Identity

Functions:

* `get_system_identity()`

* `inspect_capabilities()`

* `list_available_tools()`

* `get_model_capabilities()`

* `get_runtime_environment()`

* `generate_capability_report()`

Maintain a structured record of application version, enabled modules, supported tools, inference capabilities, permission boundaries, resource limits, and known limitations.

The identity module describes actual capabilities; it must never claim an integration or tool exists unless the corresponding implementation has passed its health check.

### 5.2 Self-Diagnostics

Functions:

* `run_health_check()`

* `check_dependencies()`

* `check_database_integrity()`

* `check_model_runtime()`

* `check_storage_capacity()`

* `inspect_recent_errors()`

* `diagnose_failed_job(job_id)`

* `generate_diagnostic_report()`

Check application startup, database migrations, storage permissions, job queue health, model availability, worker heartbeats, scheduled jobs, log errors, and backup freshness.

Diagnostics must distinguish warnings from confirmed failures and avoid exposing secrets in reports.

### 5.3 Self-Research

Functions:

* `create_research_job()`

* `discover_relevant_sources()`

* `fetch_documentation()`

* `inspect_repository()`

* `extract_findings()`

* `compare_sources()`

* `record_source_provenance()`

* `create_research_report()`

Capabilities:

* Search documentation and public repositories when network access is enabled.

* Study error messages and dependency documentation.

* Research improvements for an existing skill or workflow.

* Track source URLs, retrieval timestamps, version information, and relevant excerpts.

* Separate observed facts, hypotheses, and proposed changes.

* Save reports locally for later retrieval.

Web pages, repositories, issue comments, and downloaded skill files are untrusted inputs. Research content must not be treated as executable instructions or allowed to override policies.

### 5.4 Self-Evaluation

Functions:

* `create_evaluation_suite()`

* `run_benchmark()`

* `evaluate_task_outcome()`

* `measure_tool_selection()`

* `measure_completion_rate()`

* `compare_agent_versions()`

* `detect_regressions()`

* `publish_evaluation_report()`

Evaluation dimensions:

* Task completion rate.

* Correctness and output validity.

* Tool selection and execution reliability.

* Number of unnecessary tool calls.

* Recovery success.

* Latency and resource consumption.

* Policy violations and approval handling.

* Memory retrieval relevance.

* Skill regression rate.

Use a fixed, versioned test set for comparisons. A language model's self-assessment alone is not proof of correctness; use deterministic tests, expected outputs, and external evidence where applicable.

### 5.5 Self-Goals

Functions:

* `create_improvement_goal()`

* `break_goal_into_milestones()`

* `generate_candidate_tasks()`

* `track_goal_progress()`

* `evaluate_goal_completion()`

* `pause_goal()`

* `cancel_goal()`

* `archive_goal()`

Every goal must include an objective, baseline measurement, target, deadline or review interval, permitted tools, resource budget, completion criteria, and rollback requirements where applicable.

Goals may create work automatically within approved limits. They cannot grant themselves new permissions or remove approval requirements.

### 5.6 Self-Skills

Functions:

* `draft_skill()`

* `validate_skill_manifest()`

* `inspect_skill_dependencies()`

* `run_skill_tests()`

* `evaluate_skill_quality()`

* `publish_skill_version()`

* `disable_skill()`

* `rollback_skill_version()`

* `record_skill_provenance()`

Each skill must have:

* A unique identifier and human-readable name.

* Purpose, instructions, and supported use cases.

* Input and output schemas where appropriate.

* Required tools and declared permissions.

* Dependencies and compatibility requirements.

* Version number, origin, and creation timestamp.

* Tests, known limitations, and last evaluation results.

* Enabled/disabled status and rollback history.

Skill creation must use staged publication: draft, validate, test, evaluate, approve if required, then publish. Imported skills must never execute automatically merely because they were discovered online.

### 5.7 Self-Memory

Functions:

* `store_memory()`

* `retrieve_memories()`

* `update_memory()`

* `detect_memory_conflicts()`

* `mark_memory_stale()`

* `delete_memory()`

* `export_memory()`

* `restore_memory_snapshot()`

Memory categories:

* User-approved preferences.

* Project and task context.

* Successful procedures.

* Failures and lessons learned.

* Research findings and citations.

* Skill provenance and evaluations.

* System observations and diagnostic history.

Store timestamps, provenance, confidence where relevant, and revision history. Support user inspection, correction, export, and deletion. Sensitive information must not be collected unnecessarily.

### 5.8 Self-Repair and Self-Recovery

Functions:

* `classify_failure()`

* `propose_repair()`

* `create_isolated_repair_workspace()`

* `apply_candidate_patch()`

* `run_repair_tests()`

* `create_checkpoint()`

* `restore_checkpoint()`

* `resume_interrupted_job()`

* `verify_recovery()`

Repair workflow:

* Detect and classify the failure.

* Preserve logs and create a recovery point.

* Diagnose the likely cause.

* Propose a narrowly scoped fix.

* Apply the candidate in an isolated workspace.

* Run relevant tests and security checks.

* Request approval for protected changes.

* Apply the approved patch and verify the result.

* Roll back if health checks fail.

* Record the outcome to prevent repeated unsuccessful repairs.

The system must not autonomously disable authentication, weaken sandboxing, change trusted security policies, or grant itself elevated permissions to resolve a failure.

### 5.9 Self-Improvement Manager

Functions:

* `analyze_performance_history()`

* `identify_improvement_opportunities()`

* `rank_improvement_proposals()`

* `estimate_change_risk()`

* `schedule_improvement_trial()`

* `compare_before_after_metrics()`

* `approve_improvement()`

* `reject_improvement()`

* `rollback_improvement()`

Prioritize changes by expected benefit, confidence, implementation cost, risk, and resource use.

Improvement proposals must state the problem, supporting evidence, expected benefit, test plan, affected modules, required permissions, acceptance criteria, and rollback method.

The engine should prefer small, reversible improvements over broad self-modification.

### 6\. Autonomous agents, tools, and workflow engine

### 6.1 Agent orchestrator

Implement the following services:

* Planner: converts a user objective into structured steps, dependencies, and completion criteria.

* Executor: executes permitted actions through registered tools.

* Verifier: checks outputs against explicit acceptance criteria.

* Scheduler: creates and triggers scheduled work.

* Worker manager: manages concurrent tasks and resource budgets.

* Goal manager: maintains long-running objectives and milestones.

* Memory retriever: provides relevant, permission-appropriate context.

* Recovery manager: resumes recoverable jobs and handles failures.

* Approval manager: blocks sensitive operations until approved.

* Audit manager: records significant actions and outcomes.

Workers must have configurable concurrency limits, timeouts, retry policies, and cancellation behavior. Long-running jobs must persist their state so that restarting the application does not silently erase their status.

### 6.2 Tool registry

Each tool must declare a stable identifier, description, input schema, output schema, permission requirements, timeout, supported platforms, and risk classification.

| Tool category | Functions                                                                        |
| ------------- | -------------------------------------------------------------------------------- |
| Filesystem    | List, search, read, create, edit, copy, move, rename, and delete permitted files |
| Terminal      | Execute approved commands in a restricted working directory                      |
| Browser       | Navigate, extract page content, fill forms, and perform approved interactions    |
| Documents     | Extract and transform supported document formats                                 |
| Research      | Search sources, retrieve documents, summarize, and cite findings                 |
| Productivity  | Create tasks, edit notes, and manage reminders                                   |
| Memory        | Store, search, revise, and retrieve permitted memories                           |
| Scheduler     | Schedule tasks, pause jobs, resume jobs, and inspect run history                 |
| Git           | Inspect repositories, create branches, generate diffs, and run tests             |
| Notifications | Send approved local or configured external notifications                         |
| MCP           | Connect to explicitly configured Model Context Protocol servers                  |

MCP servers, browser sessions, terminal tools, and imported skills must be treated as separate trust boundaries.

### 6.3 Workflow builder

The Web UI must provide a visual or form-based workflow editor.

Required features:

* Create a workflow from predefined steps or a plain-language request.

* Define triggers: manual, scheduled, or supported application events.

* Add conditions, branches, and dependent steps.

* Configure inputs, outputs, retry behavior, and timeouts.

* Select the tools and permissions each step may use.

* Preview the execution plan before activation.

* Run a test execution with sample data.

* Pause, resume, duplicate, disable, and version workflows.

* Inspect each execution's logs and outputs.

* Require approval for configured sensitive steps.

The workflow engine must validate dependency cycles and invalid inputs before activating a workflow.

### 7\. Model management and inference

Keep inference behind a stable adapter interface so LifeOps and Self-X do not depend on a specific model provider.

### Required adapter operations

* Detect runtime and version.

* Validate model path and compatibility.

* Report model metadata and supported capabilities.

* Start and stop inference sessions.

* Submit requests and return structured results.

* Stream tokens when supported.

* Cancel requests when supported.

* Report runtime health and errors.

* Apply configured timeouts and resource limits.

### Model Manager page

The page must include:

* Active model and runtime.

* Available model list and paths.

* Add, remove, rescan, and select model actions.

* Model compatibility and health status.

* Context length and generation parameters where supported.

* Temperature, top-p, maximum output tokens, and seed when supported.

* Inference logs and error details with secret redaction.

* Resource usage where available.

* A test prompt and output preview.

* Optional remote provider configuration, if enabled by the deployment profile.

Do not expose unsupported settings as working controls. A runtime-specific setting should be displayed as unsupported or unavailable when it cannot be applied.

Recommended initial profile: local-first inference with LiteRT-LM support, while keeping other local runtimes optional. A LiteRT-only deployment must be achievable through configuration without introducing alternative inference providers.

### 8\. Complete settings specification

All settings must be accessible through the Web UI, validated by the backend, persisted appropriately, and documented. Use sensible defaults, explicit ranges, safe fallback behavior, and clear descriptions.

| Settings section | Required options                                                            |
| ---------------- | --------------------------------------------------------------------------- |
| General          | Application name, language, time zone, date format, startup behavior        |
| Appearance       | Dark/light/system theme, accent color, density, sidebar state               |
| Dashboard        | Visible widgets, refresh interval, default landing page                     |
| Assistant        | Response preferences, confirmation behavior, task planning, output limits   |
| Model            | Runtime, model selection, context size, supported generation parameters     |
| Memory           | Enable/disable categories, retrieval limits, retention, indexing, export    |
| Tasks            | Default priority, reminder timing, recurring-task behavior, overdue rules   |
| Calendar         | Time zone, week start, working hours, default event duration                |
| Notifications    | Enabled channels, quiet hours, event types, retry policy                    |
| Research         | Network access, approved domains, retrieval limits, source requirements     |
| Browser          | Allowed domains, downloads, cookies/session behavior, action approvals      |
| Terminal         | Allowed commands, working directories, timeouts, sandbox restrictions       |
| Files            | Allowed directories, exclusions, indexing limits, delete confirmations      |
| Skills           | Import policy, test requirements, enabled skills, publication permissions   |
| Self-X           | Enabled modules, review interval, improvement budget, auto-promotion policy |
| Scheduler        | Worker concurrency, job limits, retry count, timeout, missed-run handling   |
| Security         | Authentication, sessions, roles, CSRF protections, network binding          |
| Privacy          | Local data retention, export, deletion, telemetry policy                    |
| Storage          | Database location, attachment paths, retention, backup location             |
| Recovery         | Checkpoint policy, retry behavior, rollback rules, restore verification     |
| Integrations     | Enable/disable adapters, credentials, scopes, health checks                 |
| Performance      | CPU limits, memory budget, queue limits, indexing concurrency               |
| Updates          | Update checks, release channel, maintenance window, rollback policy         |
| Donations        | Optional donation URL, public project information, disable/hide option      |

### 8.1 Recommended autonomy profiles

Assist Mode

Safest

The assistant proposes plans and actions; the user explicitly approves execution.

Supervised Mode

Low-risk actions can run under configured permissions. Sensitive actions require approval.

Bounded Autonomous Mode

Pre-authorized tasks and workflows can execute within defined resource, tool, and time limits. High-risk actions remain blocked or approval-gated.

Autonomy profiles are convenience presets, not replacements for the policy engine. Switching profiles must not bypass hard security restrictions.

### 8.2 Settings implementation rules

* Store non-secret settings in a validated configuration table or configuration file.

* Store credentials in the operating system's secret store when available; otherwise use a protected local secret file with documented limitations.

* Never put provider secrets in HTML, browser JavaScript, URLs, or client-side storage.

* Apply configuration changes atomically where practical.

* Record changes to security-relevant settings in the audit log.

* Require explicit confirmation before changing network exposure or weakening security.

* Provide restore-defaults, export-settings, and import-settings functions.

* Back up settings before applying potentially disruptive changes.

* Validate settings again at execution time; do not rely solely on browser validation.

### 9\. Security and trust model

Use three execution policy decisions:

* `ALLOW` — the action is permitted under the current policy.

* `ASK` — the action requires explicit approval.

* `BLOCK` — the action is forbidden.

### Security requirements

* Require authentication when accessing the application beyond a deliberately configured trusted local session.

* Bind to loopback by default; require explicit configuration and authentication before LAN exposure.

* Protect state-changing web requests against CSRF and enforce session protections.

* Validate every request using backend schemas.

* Apply rate limits and resource budgets.

* Enforce path restrictions and defend against path traversal and symbolic-link escapes.

* Use least-privilege execution and isolated workspaces for risky operations.

* Treat webpages, uploaded documents, repositories, and external instructions as untrusted.

* Redact secrets and sensitive personal data from logs.

* Require approval for destructive file operations, external messages, publishing, and protected system modifications.

* Provide a global stop control for agent execution and a safe worker shutdown procedure.

* Maintain an append-oriented audit trail for approvals, tool actions, configuration changes, and recovery events.

* Encrypt backups when practical and verify backup integrity.

* Never allow model output alone to authorize an action.

* Never let Self-X silently increase its permissions or disable security controls.

The emergency stop must prevent new agent actions and request cancellation of active jobs. The interface must clearly report if a tool cannot be interrupted immediately.

### 10\. Database and persistent storage design

Use SQLite for the first release, with SQLAlchemy models and versioned database migrations. Keep large attachments and generated artifacts in a managed local workspace rather than storing all file bytes directly in database rows.

### Required tables

| Table                 | Purpose                                       |
| --------------------- | --------------------------------------------- |
| users                 | Local users and account metadata              |
| sessions              | Session identifiers, expiry, and revocation   |
| settings              | Validated application configuration           |
| projects              | Personal and agent project records            |
| tasks                 | Tasks, priorities, deadlines, and status      |
| task_dependencies     | Relationships between dependent tasks         |
| calendar_events       | Events, time zones, and recurrence rules      |
| notes                 | Personal notes and knowledge entries          |
| documents             | Indexed files and document metadata           |
| document_chunks       | Extracted text segments and source locations  |
| conversations         | Conversation metadata                         |
| messages              | Messages and associated execution context     |
| memories              | Searchable, categorized memory records        |
| memory_revisions      | Memory changes and historical snapshots       |
| agent_runs            | Task execution state and results              |
| agent_steps           | Individual plan and execution steps           |
| tool_calls            | Tool inputs, outputs, status, and duration    |
| approvals             | Approval requests, decisions, and expiry      |
| skills                | Skill definitions and current version         |
| skill_versions        | Versioned skill content and provenance        |
| skill_tests           | Skill test cases and results                  |
| research_jobs         | Research execution and status                 |
| research_sources      | URLs, metadata, timestamps, and citations     |
| selfx_goals           | Improvement objectives and measurements       |
| evaluations           | Benchmarks, scores, and regression results    |
| improvement_proposals | Proposed changes, evidence, and risk          |
| checkpoints           | Recovery points and artifact references       |
| scheduled_jobs        | Recurrence, trigger configuration, and status |
| job_events            | Progress, retries, and state transitions      |
| integrations          | Integration metadata and health               |
| audit_events          | Security-relevant actions and outcomes        |
| notifications         | Reminders, delivery attempts, and read status |
| backup_records        | Backup manifests and verification status      |

### Storage requirements

* Use database transactions for related state changes.

* Add indexes for task status, due dates, run identifiers, memory search, and timestamps.

* Use foreign keys and appropriate cascading rules.

* Preserve important execution and audit history according to retention settings.

* Support database migrations, integrity checks, backup, and restore.

* Avoid storing secrets in ordinary settings or audit events.

* Use a suitable full-text search implementation for memories, notes, and extracted document text.

* Make optional vector search an extension, not a mandatory dependency for the initial release.

### 11\. Backend API specification

The Web UI must use the same application services as scheduled jobs and autonomous agents. Do not duplicate business logic in browser code.

### API groups

| API prefix           | Responsibilities                                         |
| -------------------- | -------------------------------------------------------- |
| /api/v1/auth         | Login, logout, session management                        |
| /api/v1/dashboard    | Dashboard summaries and status                           |
| /api/v1/assistant    | Conversations, plans, and task submissions               |
| /api/v1/tasks        | Task and project management                              |
| /api/v1/calendar     | Events, recurring schedules, and reminders               |
| /api/v1/notes        | Notes and knowledge management                           |
| /api/v1/memory       | Memory CRUD, search, revisions, and export               |
| /api/v1/documents    | File indexing and document operations                    |
| /api/v1/research     | Research jobs, sources, and reports                      |
| /api/v1/skills       | Skill authoring, tests, versions, and publication        |
| /api/v1/selfx        | Diagnostics, goals, evaluation, and improvements         |
| /api/v1/agents       | Agent runs, execution plans, status, and cancellation    |
| /api/v1/tools        | Tool discovery, configuration, and health                |
| /api/v1/models       | Model inventory, runtime detection, and inference health |
| /api/v1/workflows    | Workflow definitions, versions, and execution            |
| /api/v1/scheduler    | Scheduled jobs and worker status                         |
| /api/v1/approvals    | Approval queue and decisions                             |
| /api/v1/settings     | Read, validate, and update settings                      |
| /api/v1/audit        | Filtered audit history                                   |
| /api/v1/backups      | Backup creation, verification, and restoration           |
| /api/v1/integrations | Integration configuration and connection health          |
| /api/v1/system       | Health, version, diagnostics, and shutdown status        |

Use consistent JSON response schemas, appropriate HTTP status codes, request validation, pagination, and error identifiers. Long-running operations must return a job identifier rather than blocking a web request until completion.

### Real-time events

Use WebSockets or server-sent events for:

* Agent execution progress.

* Tool-call status.

* Job queue and worker health.

* Approval requests.

* Research progress.

* Self-X diagnostics and evaluation runs.

* Notifications and system health changes.

Authenticate real-time connections and enforce per-user access to every event stream.

### Example endpoint contracts

```text
POST   /api/v1/assistant/messages
POST   /api/v1/agents/runs
GET    /api/v1/agents/runs/{run_id}
POST   /api/v1/agents/runs/{run_id}/cancel

GET    /api/v1/approvals
POST   /api/v1/approvals/{approval_id}/decision

POST   /api/v1/selfx/diagnostics
POST   /api/v1/selfx/evaluations
POST   /api/v1/selfx/improvements
POST   /api/v1/selfx/improvements/{id}/approve
POST   /api/v1/selfx/improvements/{id}/rollback

GET    /api/v1/skills
POST   /api/v1/skills
POST   /api/v1/skills/{id}/test
POST   /api/v1/skills/{id}/publish

POST   /api/v1/backups
POST   /api/v1/backups/{id}/verify
POST   /api/v1/backups/{id}/restore
```

These paths define the intended API contract. Each endpoint must be implemented, tested, authenticated, and connected to the corresponding service before it is presented as operational.

### 12\. Complete project folder structure

Use a modular monolith for the first release. This keeps installation and maintenance straightforward while preserving clear boundaries between subsystems.

```text

lifeops-selfx/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── .gitignore
├── .env.example
├── config/
│   ├── defaults.toml
│   ├── logging.toml
│   └── permissions.toml
├── scripts/
│   ├── install_windows.ps1
│   ├── install_linux.sh
│   ├── start_windows.ps1
│   ├── start_linux.sh
│   ├── backup.py
│   ├── restore.py
│   └── doctor.py
├── src/
│   └── lifeops/
│       ├── __init__.py
│       ├── app.py
│       ├── cli_admin.py
│       ├── config.py
│       ├── logging_config.py
│       ├── api/
│       │   ├── auth.py
│       │   ├── dashboard.py
│       │   ├── assistant.py
│       │   ├── tasks.py
│       │   ├── calendar.py
│       │   ├── notes.py
│       │   ├── memory.py
│       │   ├── documents.py
│       │   ├── research.py
│       │   ├── skills.py
│       │   ├── selfx.py
│       │   ├── agents.py
│       │   ├── tools.py
│       │   ├── models.py
│       │   ├── workflows.py
│       │   ├── scheduler.py
│       │   ├── approvals.py
│       │   ├── settings.py
│       │   ├── audit.py
│       │   ├── backups.py
│       │   └── system.py
│       ├── web/
│       │   ├── layout.py
│       │   ├── components/
│       │   ├── pages/
│       │   ├── templates/
│       │   └── static/
│       │       ├── css/
│       │       ├── js/
│       │       ├── icons/
│       │       └── images/
│       ├── core/
│       │   ├── planner.py
│       │   ├── executor.py
│       │   ├── verifier.py
│       │   ├── orchestrator.py
│       │   ├── worker_manager.py
│       │   ├── scheduler.py
│       │   └── task_states.py
│       ├── lifeops/
│       │   ├── tasks.py
│       │   ├── projects.py
│       │   ├── calendar.py
│       │   ├── reminders.py
│       │   ├── routines.py
│       │   ├── notes.py
│       │   ├── documents.py
│       │   ├── daily_planner.py
│       │   ├── notifications.py
│       │   └── analytics.py
│       ├── selfx/
│       │   ├── identity.py
│       │   ├── diagnostics.py
│       │   ├── repair.py
│       │   ├── research.py
│       │   ├── evaluation.py
│       │   ├── goals.py
│       │   ├── skills.py
│       │   ├── memory.py
│       │   ├── recovery.py
│       │   └── improvement.py
│       ├── models/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── litert_adapter.py
│       │   └── optional_adapters.py
│       ├── tools/
│       │   ├── registry.py
│       │   ├── filesystem.py
│       │   ├── terminal.py
│       │   ├── browser.py
│       │   ├── documents.py
│       │   ├── git.py
│       │   ├── research.py
│       │   └── mcp.py
│       ├── workflows/
│       │   ├── engine.py
│       │   ├── definitions.py
│       │   ├── validation.py
│       │   └── triggers.py
│       ├── security/
│       │   ├── auth.py
│       │   ├── sessions.py
│       │   ├── policy.py
│       │   ├── approvals.py
│       │   ├── sandbox.py
│       │   ├── secrets.py
│       │   └── audit.py
│       ├── storage/
│       │   ├── database.py
│       │   ├── models.py
│       │   ├── repositories.py
│       │   ├── migrations/
│       │   ├── memory_index.py
│       │   └── backup.py
│       └── integrations/
│           ├── base.py
│           ├── calendar/
│           ├── email/
│           ├── messaging/
│           └── webhooks/
├── skills/
│   ├── builtins/
│   └── examples/
├── workspace/
│   ├── tasks/
│   ├── research/
│   ├── skills_staging/
│   └── repair_sandboxes/
├── data/
│   └── .gitkeep
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── api/
│   ├── web/
│   ├── security/
│   ├── recovery/
│   └── e2e/
└── docs/
    ├── architecture.md
    ├── installation.md
    ├── configuration.md
    ├── security.md
    ├── api.md
    ├── skills.md
    ├── selfx.md
    ├── backup-recovery.md
    └── troubleshooting.md
```

This is the target organization, not a claim that those files already exist. Keep the first release cohesive; do not create empty modules just to fill the directory tree.

### 13\. Installation and deployment requirements

The project must include complete installation instructions for Windows 10/11 and Linux. Docker must not be required.

### Windows installation

Prerequisites: a supported Python version, Git (optional for downloading source), and a compatible model runtime if local inference is enabled.

The repository should provide PowerShell scripts that:

* Check Python and dependency versions.

* Create a virtual environment.

* Install pinned project dependencies.

* Create the local data and workspace directories.

* Generate a local configuration file from documented defaults.

* Initialize and migrate the SQLite database.

* Create the initial administrator account securely.

* Run dependency and model-runtime diagnostics.

* Start the application on loopback by default.

* Display the local Web UI address and troubleshooting information.

Example intended workflow:

```powershell
git clone https://github.com/YOUR_USERNAME/lifeops-selfx.git
cd lifeops-selfx

.\scripts\install_windows.ps1
.\scripts\start_windows.ps1
```

The scripts must be implemented and tested before these commands are documented as supported.

### Linux installation

The Linux installer should perform equivalent checks, use a Python virtual environment, create directories with appropriate permissions, initialize the database, and start the application.

```bash
git clone https://github.com/YOUR_USERNAME/lifeops-selfx.git
cd lifeops-selfx

chmod +x scripts/install_linux.sh scripts/start_linux.sh
./scripts/install_linux.sh
./scripts/start_linux.sh
```

For persistent deployments, provide optional native service integration, such as a systemd unit on Linux and a Windows service or scheduled startup task where appropriate.

### Startup and health checks

The application must expose a health-check endpoint and provide an administrator diagnostics report that identifies:

* Python and dependency compatibility.

* Database connectivity and migration status.

* Writable storage and available disk space.

* Model runtime availability.

* Background worker and scheduler health.

* Configuration errors.

* Backup and recovery status.

If the model runtime is missing, the productivity interface should remain available, while AI functions display an accurate unavailable status and remediation instructions.

### 14\. Testing and quality assurance

The project is not complete until automated tests cover the major application workflows.

| Test suite        | Required coverage                                                          |
| ----------------- | -------------------------------------------------------------------------- |
| Unit tests        | Task services, planners, memory, policies, skill validation                |
| Database tests    | Migrations, transactions, constraints, backup and restore                  |
| API tests         | Authentication, validation, permissions, errors, pagination                |
| Web UI tests      | Navigation, forms, dialogs, responsive behavior, empty states              |
| Agent tests       | Planning, tool selection, execution, verification, cancellation            |
| Self-X tests      | Diagnostics, skill evaluation, improvement proposals, rollback             |
| Security tests    | Path traversal, CSRF, session security, authorization, secret redaction    |
| Recovery tests    | Interrupted jobs, worker restarts, failed migrations, restore verification |
| Integration tests | Model adapters, browser tools, configured external integrations            |
| End-to-end tests  | Complete workflows from browser request to verified result                 |

Tests must not depend on paid AI APIs. Provide mock adapters and deterministic fixtures for ordinary CI runs. Optional real-model integration tests may be run separately when a compatible local model is installed.

### Mandatory end-to-end acceptance scenarios

* Create a task through the browser and confirm it persists after restart.

* Ask the assistant to plan a multi-step task and inspect the plan.

* Execute an allowed action and verify its output.

* Confirm a protected action cannot execute before approval.

* Search, edit, and export a memory.

* Draft a skill, run its tests, and publish an eligible version.

* Inject a known application error and verify that Self-X diagnoses it correctly.

* Propose a repair, test it in isolation, and roll it back when tests fail.

* Interrupt a background job and recover it without duplicating completed side effects.

* Back up the database, restore it into a clean test environment, and verify the restored data.

* Run the application without network access and verify the documented offline capabilities.

* Confirm that untrusted research content cannot override the security policy.

### 15\. Observability, backups, and recovery

### Observability

Implement structured application logs and a unified event timeline.

Each execution record should include:

* Task and run identifiers.

* Start time, duration, and final state.

* Tool calls and their results.

* Retry count and failure category.

* Approval references.

* Verification results.

* Resource usage when available.

Never log authentication tokens, passwords, API keys, or unrestricted sensitive document contents.

### Backup and restore

The backup manager must support:

* On-demand and scheduled backups.

* Consistent database snapshots.

* Optional inclusion of user-selected files, skills, and configuration.

* A manifest containing versions, timestamps, and file hashes.

* Optional encrypted archives.

* Backup integrity verification.

* Restore previews and destination checks.

* Recovery into a clean installation.

* Documented retention policies.

A backup is not considered verified merely because the archive exists. The system must validate its contents and provide a tested restoration procedure.

### 16\. Privacy, offline operation, and monetization

### Local-first privacy

* Keep tasks, memories, notes, and execution history on the user's machine by default.

* Make outbound network access configurable.

* Clearly identify which features require internet access.

* Keep telemetry disabled by default.

* Allow data export and deletion.

* Provide a way to inspect stored memories and indexed directories.

* Avoid silently collecting unrelated files or personal information.

### Offline-capable operation

The following should work offline after installation, provided their required local dependencies are available:

* Task and project management.

* Notes and local memory.

* Calendar and reminders.

* Local file indexing and search.

* Saved skills and workflow definitions.

* Diagnostics and evaluation using local test fixtures.

* Backup and restore.

* Inference through an available compatible local model.

Web research, remote messaging, cloud calendars, remote providers, and online update checks require connectivity and must report their status accurately.

### Optional donation support

Include an optional Support Development page with:

* Project description and development roadmap.

* Open-source license information.

* Configurable donation link.

* Clear disclosure that donations are voluntary.

* An option to hide donation prompts.

Core functionality must not depend on donations. Do not include hardcoded payment credentials or collect payment information directly in the application.

### 17\. Development and release phases

* Phase 1 — Application foundation: configuration, authentication, database, migrations, responsive Web UI shell, logging, health checks.

* Phase 2 — LifeOps essentials: tasks, projects, calendar, reminders, notes, local document indexing, memory search.

* Phase 3 — Agent runtime: model adapter, planner, executor, tool registry, approvals, job queue, cancellation, verification.

* Phase 4 — Self-X: identity, diagnostics, research, evaluation, goals, skill lifecycle, recovery, and improvement proposals.

* Phase 5 — Automation: scheduler, persistent workflows, bounded background workers, notifications, optional integrations.

* Phase 6 — Reliability: complete security tests, fault injection, backup/restore validation, performance limits, Windows/Linux compatibility.

* Phase 7 — Release: documentation, setup scripts, sample configuration, reproducible builds, changelog, release checklist.

### 18\. Final instructions for the coding agent

Implement LifeOps AI + Self-X Evolution Engine in the target GitHub repository as a complete, functional application.

Begin by inspecting the repository, identifying its existing architecture, dependencies, completed functionality, missing files, and failing tests. Preserve working functionality and avoid unnecessary rewrites.

Before implementation, create or update the architecture document and a feature acceptance checklist. Then implement the project in small, testable phases.

For every feature:

1. Implement the backend service and data model.
2. Add the required database migration.
3. Implement API routes with validation and authorization.
4. Connect the Web UI to real backend functionality.
5. Add settings, error handling, and relevant audit events.
6. Write and execute automated tests.
7. Update the documentation and acceptance checklist.

Do not report files as implemented unless they exist. Do not report tests as passing unless they were actually executed successfully. Do not claim an external integration works unless it has been validated.

Prioritize security, reliable execution, persistent storage, observable behavior, and recoverability over superficial feature counts.

The final deliverable must include the complete source tree, working Web UI, backend, configuration, migrations, installation scripts, tests, documentation, and a report identifying implemented features, remaining limitations, and verified test results.

Do not stop after producing a plan or initial dashboard. Continue implementing the remaining features until the agreed acceptance criteria are met, or clearly document any genuine blocker.

### 19\. Definition of done

The initial release is complete when:

* The Web UI is functional and all advertised controls work.

* LifeOps can manage tasks, notes, reminders, and local knowledge.

* The configured model can execute approved agent workflows through the application.

* Self-X can diagnose failures, evaluate skills, propose improvements, and recover eligible failures.

* The policy engine independently enforces permissions and approval requirements.

* SQLite persistence, migrations, backups, and recovery are tested.

* Installation and startup work on the supported Windows and Linux environments.

* Offline functionality behaves as documented.

* Automated tests run successfully, with any remaining failures disclosed.

* Every feature has documented configuration, error handling, and acceptance criteria.

My recommendation: build the modular monolith first, with a polished Web UI and a reliable task execution engine. Then add Self-X's skill learning and controlled self-improvement. This approach gives you a usable personal assistant early while building toward the larger autonomous system without turning the project into an unmaintainable collection of disconnected features.

14

---

## 20. Repository implementation contract and current execution priorities

This section supplements the product requirements above. Treat the repository as an existing application: inspect its real files, preserve working behavior, and implement the next smallest complete vertical slice rather than generating a disconnected replacement project.

### 20.1 Required engineering workflow

For every implementation pass:

1. Inspect the target branch, repository tree, relevant source files, tests, dependency constraints, and recent commits before editing.
2. Keep changes focused, typed, documented, and compatible with Python 3.12+ on Windows 10/11 and Linux.
3. Add or update automated tests with each behavior change. Test validation failures, security boundaries, failure paths, and success paths.
4. Run the relevant tests and quality checks when an execution environment is available. If they cannot be run, report that limitation explicitly; never label unrun tests as passing.
5. Update user-facing documentation and configuration examples in the same change.
6. Keep credentials, session secrets, personal data, local databases, and backups out of source control.
7. Commit related changes with descriptive messages. Use a feature branch and pull request for broad changes; do not claim a change is merged unless it is on the default branch.
8. Report the exact branch, commit, files changed, test commands/results, known limitations, and the next concrete implementation step.

Do not replace existing code with scaffolding merely to make a feature appear complete. No dead buttons, simulated health checks, fake integration status, fabricated test results, or unsupported success claims.

### 20.2 Model adapter requirements

Implement model support through a small, stable adapter interface. A provider preset is configuration metadata, not proof that the endpoint, credentials, model, or free quota are available.

Required initial compatibility targets:

- Local OpenAI-compatible servers: Ollama, LM Studio, and vLLM.
- Optional hosted OpenAI-compatible APIs: Groq, Cerebras, OpenRouter, Gemini's compatible endpoint, and Hugging Face's router, subject to each provider's current terms and availability.
- A future LiteRT-LM adapter only after its installed CLI, commands, output format, cancellation behavior, and supported model formats have been detected and verified against real documentation/runtime behavior.

Security and reliability requirements:

- Read credentials from environment variables or a dedicated secret store; never persist or display secret values in ordinary settings, logs, provider metadata, or audit events.
- Validate endpoint schemes and reject URL credentials, query strings, and fragments. Do not allow user-configured endpoints to silently bypass the application's outbound-network policy.
- Set bounded timeouts, cap response sizes, validate response structure, sanitize provider errors, and never log authorization headers or full secret-bearing requests.
- Keep protocol fields such as model, messages, and stream under adapter control. Validate generation parameters and response types.
- Distinguish “configured” from “reachable,” “authenticated,” and “model available.” Health checks must be explicit, bounded network probes and must not run merely because a settings page was opened.
- Do not claim a hosted provider is free. Mark free tiers and quotas as time-sensitive and require users to confirm current provider terms.
- Make streaming, cancellation, retries, model discovery, and failover capability-specific. Do not advertise them until implemented and tested.
- Failover must be opt-in, bounded, auditable, and respect data-sharing policy; never send private prompts to another provider without clear user configuration.
- Keep local inference as the default path where configured. Remote inference must be explicit and disclose that prompt data leaves the device.

### 20.3 Provider settings and integration slice

Build the model settings feature end-to-end, not as a static catalog:

1. Present provider presets and a custom-endpoint option with safe defaults.
2. Let users select a provider and enter a model identifier; store non-secret settings persistently using validated schemas.
3. Refer to secrets by environment-variable name or secret-store key. Provide setup guidance without accepting or redisplaying raw secret values through ordinary settings APIs.
4. Offer separate actions for “Save configuration,” “Test connection,” and “Discover models” only when their corresponding service operations are implemented.
5. Display distinct states for unconfigured, configured, reachable, authentication failure, model missing, and provider error.
6. Never perform a network request on page load or when listing presets.
7. Add service, route, UI, and security tests, including SSRF/private-network policy cases for custom URLs.
8. Document each provider's base URL, credential variable, model identifier requirements, privacy implications, and known limitations.

### 20.4 Persistence, execution, and Self-X priorities

Implement these as sequenced, testable releases:

- **P0 — Verify the foundation:** confirm installation, configuration, database startup, authentication/session/CSRF behavior, health reporting, Windows/Linux compatibility, and CI. Fix actual failures before adding more features.
- **P1 — Persistent model configuration:** schemas, storage, safe provider catalogue, model settings UI, explicit connection test, and honest status reporting.
- **P2 — Controlled inference service:** adapter registry, request limits, redacted audit metadata, cancellation/timeouts, normalized errors, and tests using mocked HTTP responses plus optional local-server integration tests.
- **P3 — Durable jobs:** persisted job state transitions, idempotent enqueueing, worker heartbeats, cancellation semantics, bounded retries, restart recovery, and visible progress in the UI.
- **P4 — Approval-to-execution path:** connect approval decisions to a policy-enforced executor. Deny by default for unknown tools and sensitive operations; validate permissions again immediately before execution; record outputs and verification evidence.
- **P5 — Self-X diagnostics and evaluation:** real dependency/database/worker/model checks, repeatable evaluation suites, regression comparisons, proposal review, checkpoints, and rollback of approved changes. Diagnostics must not mutate the system.
- **P6 — Integrations and skills:** add one integration at a time with least-privilege scopes, explicit configuration, health checks, permission policies, fixtures, and end-to-end tests.
- **P7 — Release hardening:** migrations from real prior schemas, backup/restore drills, accessibility, browser tests, dependency/security review, packaging, and documented upgrade/rollback paths.

Do not skip a release gate because a feature is described in this master prompt. Mark each capability as implemented, partial, planned, or blocked based on repository evidence.

### 20.5 Definition of done

A feature is done only when its implementation, validation, tests, documentation, and UI behavior agree. The UI must not imply that an operation succeeded before the service confirms it. Network calls, destructive actions, remote data transfer, and privileged execution must be visible and governed by explicit policy.

For each release, publish a concise capability matrix:

| Capability | Status | Evidence required |
| --- | --- | --- |
| Implemented | Working end-to-end | Source paths and passing relevant tests |
| Partial | Some paths work | Explicit limitations and missing paths |
| Planned | Not implemented yet | No success claims |
| Blocked | Depends on unresolved issue | Blocker and next action |

A green local test run is not a substitute for CI, and a configured adapter is not proof of provider availability. Keep the default server bound to loopback until the complete authentication, CSRF, origin, and execution security review has passed.

---

## 21. Live repository checkpoint — 2026-10-12

This checkpoint records repository evidence and supplements (but does not replace) the requirements above. Treat the status below as a snapshot; re-inspect the repository and latest CI results before relying on it.

### 21.1 Existing repository and implementation baseline

- Default branch: `main`.
- Active implementation branch at this checkpoint: `feat/local-auth-session-foundation`.
- Runtime target: Python 3.12+, Windows 10/11 and Linux.
- Existing application includes browser pages and persisted services for tasks, notes, projects, memories, approvals, agent-run records, Self-X goals, and improvement proposals.
- Existing security-related work includes password hashing, opaque cookie sessions, and request-origin/CSRF checks; these still require full end-to-end security review.
- The README explicitly identifies the application as a development build and documents important release blockers. Keep those limitations visible until evidence changes.

### 21.2 Model adapter progress on the feature branch

The following files have been added or updated on `feat/local-auth-session-foundation`; these changes are not assumed to be merged into `main`:

- `src/lifeops/models/openai_compatible.py`: synchronous, non-streaming OpenAI-compatible chat-completions adapter; reads API keys from environment variables, bounds timeouts, validates endpoint URLs and response shape, and sanitizes provider errors.
- `src/lifeops/models/provider_catalog.py`: explicit presets for local Ollama, LM Studio, and vLLM endpoints, plus optional hosted Groq, Cerebras, OpenRouter, Gemini-compatible, and Hugging Face endpoints.
- `tests/unit/test_openai_compatible.py` and `tests/unit/test_provider_catalog.py`: unit coverage for adapter validation, request behavior, safe metadata, and preset construction.
- `docs/model-providers.md`: provider setup and privacy notes.

These files are a foundation, not an end-to-end model-management feature. Preset listing and adapter construction do not prove a provider is reachable, a key is valid, a model exists, or a hosted tier is free. The current adapter does not yet provide streaming, cancellation, discovery, retries, or failover. Do not wire it to autonomous execution until policy checks and approval enforcement are verified.

### 21.3 Verification status

At the time this checkpoint was written, the GitHub connector reported no combined status checks and no workflow runs for the latest provider-catalog commit. Therefore, CI and test success are **unverified**, not passing. Re-check GitHub Actions and run the documented checks in a real supported environment.

### 21.4 Next implementation slice — persistent model settings

Implement the next vertical slice on the feature branch, preserving the current app and tests:

1. Inspect the actual storage models, service layer, API router, app settings page, authentication dependencies, and migration setup before editing.
2. Add a persistent, validated model-provider configuration that stores provider ID, model identifier, endpoint override when allowed, timeout, and the *name* of a credential environment variable—not its secret value.
3. Ensure settings responses, audit events, HTML, exceptions, and logs never expose credentials. Do not accept an API-key value in ordinary settings forms.
4. Add an authenticated settings UI for selecting a known provider, setting the model identifier, and saving non-secret configuration. Keep the currently selected provider clearly distinct from connection health.
5. Add an explicit “Test connection” operation only if it performs a bounded, opt-in network request and returns a sanitized status. Do not probe providers on page load.
6. Enforce outbound endpoint policy for custom URLs, including loopback/local-only policy defaults and protection against unsafe schemes and unexpected private-network targets. A custom endpoint must not become an SSRF bypass.
7. Add storage/service/API/UI tests for valid saves, invalid inputs, unauthorized access, secret redaction, local endpoints, hosted credentials missing, provider failures, and no network calls during page render.
8. Update documentation and the capability matrix. Run tests if an execution environment is available; otherwise state that they were not run.
9. Commit the implementation to the feature branch and open or update a pull request for review. Do not silently merge broad security-sensitive changes into `main`.

After this slice, continue through controlled inference, durable jobs and cancellation, approval-to-execution wiring, real Self-X diagnostics/evaluations, integrations, and release hardening in the order defined in section 20.4. Each slice must include code, tests, docs, and honest verification results; do not treat this checkpoint as permission to skip review or claim the whole platform is complete.
