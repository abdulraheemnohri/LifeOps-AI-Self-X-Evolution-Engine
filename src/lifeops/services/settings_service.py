"""Settings service implementing spec section 8: validated, persisted config
with defaults, autonomy profiles, export/import, restore-defaults, and audit
of security-relevant changes."""
import copy
import json
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session as DBSession

from lifeops.storage.models import Setting
from lifeops.security.policy import log_audit_event

# Full settings schema per Prompt.md section 8 (section -> option -> default).
DEFAULT_SETTINGS: Dict[str, Dict[str, Any]] = {
    "general": {"app_name": "LifeOps AI + Self-X Evolution Engine", "language": "en",
                 "time_zone": "UTC", "date_format": "YYYY-MM-DD", "startup_behavior": "restore_last_session"},
    "appearance": {"theme": "dark", "accent_color": "#38bdf8", "density": "comfortable", "sidebar_collapsed": False},
    "dashboard": {"visible_widgets": ["tasks", "health", "approvals", "activity"], "refresh_interval_seconds": 30,
                   "default_landing_page": "/"},
    "assistant": {"response_style": "concise", "confirm_before_executing": True, "auto_plan_tasks": True,
                   "max_output_tokens": 2048},
    "model": {"runtime": "litert", "model_path": "", "context_length": 4096,
               "generation_params": {"temperature": 0.7, "top_p": 0.95, "max_tokens": 2048, "seed": None}},
    "memory": {"enabled_categories": ["preferences", "facts", "procedures"], "retrieval_limit": 20,
                "retention_days": 365, "auto_index": True, "export_enabled": True},
    "tasks": {"default_priority": "medium", "reminder_minutes_before": 30,
               "recurring_behavior": "create_next_instance", "overdue_rule": "notify"},
    "calendar": {"time_zone": "UTC", "week_start": "monday", "working_hours": {"start": "09:00", "end": "17:00"},
                  "default_event_duration_minutes": 60},
    "notifications": {"channels": ["in_app"], "quiet_hours": {"start": "22:00", "end": "07:00"},
                       "event_types": ["approval_request", "task_due", "job_failed"], "retry_count": 3},
    "research": {"network_access": False, "approved_domains": [], "max_sources": 10,
                  "require_citations": True, "treat_content_as_untrusted": True},
    "browser": {"allowed_domains": [], "downloads_enabled": False, "cookie_policy": "session_only",
                 "action_approvals": True},
    "terminal": {"allowed_commands": [], "working_directories": ["workspace"], "timeout_seconds": 30,
                  "sandbox_required": True},
    "files": {"allowed_directories": ["workspace", "data"], "exclusions": [".git", "node_modules"],
               "max_index_files": 5000, "delete_confirmation": True},
    "skills": {"import_policy": "review_required", "tests_required_for_publish": True,
                "enabled_skills": [], "publication_requires_approval": True},
    "selfx": {"enabled_modules": ["identity", "diagnostics", "memory", "skills", "recovery", "improvement"],
               "review_interval_hours": 24, "improvement_budget_per_day": 3, "auto_promotion": "disabled"},
    "scheduler": {"worker_concurrency": 2, "max_jobs_per_run": 50, "retry_count": 2,
                   "timeout_seconds": 300, "missed_run_policy": "skip"},
    "security": {"auth_enabled": False, "session_timeout_hours": 24, "roles": {"admin": ["*"]},
                  "csrf_protection": True, "network_binding": "127.0.0.1"},
    "privacy": {"local_retention_days": 365, "export_enabled": True, "telemetry": "disabled"},
    "storage": {"database_url": "sqlite:///data/lifeops.db", "attachment_path": "data/attachments",
                 "backup_location": "data/backups", "retention_backups": 10},
    "recovery": {"checkpoint_policy": "on_mutation", "retry_behavior": "exponential_backoff",
                  "rollback_rules": "tests_gate", "verify_restore": True},
    "integrations": {"enabled_adapters": [], "health_check_interval_minutes": 15},
    "performance": {"cpu_limit_percent": 80, "memory_budget_mb": 2048, "queue_limit": 100,
                     "indexing_concurrency": 2},
    "updates": {"check_for_updates": False, "release_channel": "stable", "maintenance_window": "",
                 "rollback_policy": "automatic"},
    "donations": {"url": "", "show_banner": False, "public_info": ""},
}

AUTONOMY_PROFILES: Dict[str, Dict[str, Any]] = {
    "Assist Mode": {"description": "Safest. Assistant proposes; user approves everything.",
                     "policy_overrides": {"filesystem.read": "ASK", "filesystem.write": "ASK",
                                            "terminal.execute": "ASK", "browser.navigate": "ASK",
                                            "network.outbound": "ASK", "system.modify": "BLOCK"}},
    "Supervised Mode": {"description": "Low-risk actions run under permissions; sensitive need approval.",
                         "policy_overrides": {"filesystem.read": "ALLOW", "filesystem.write": "ASK",
                                                "terminal.execute": "ASK", "browser.navigate": "ALLOW",
                                                "network.outbound": "ASK", "system.modify": "BLOCK"}},
    "Bounded Autonomous Mode": {"description": "Pre-authorized workflows execute within limits; high-risk stays gated.",
                                 "policy_overrides": {"filesystem.read": "ALLOW", "filesystem.write": "ALLOW",
                                                        "terminal.execute": "ASK", "browser.navigate": "ALLOW",
                                                        "network.outbound": "ASK", "system.modify": "BLOCK"}},
}

# Keys whose changes must be recorded in the audit log.
SECURITY_RELEVANT_SECTIONS = {"security", "files", "terminal", "browser", "network", "research"}


class SettingsService:
    def __init__(self, db: DBSession):
        self.db = db

    def get_all(self) -> Dict[str, Any]:
        merged = copy.deepcopy(DEFAULT_SETTINGS)
        for row in self.db.query(Setting).all():
            section, _, key = row.key.partition("/")
            if key:
                merged.setdefault(section, {})[key] = row.value.get("value")
            else:
                merged[section] = row.value.get("value", {})
        return merged

    def get_section(self, section: str) -> Dict[str, Any]:
        return self.get_all().get(section, {})

    def validate(self, section: str, updates: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        if section not in DEFAULT_SETTINGS:
            return False, f"Unknown settings section '{section}'"
        for key in updates:
            if key not in DEFAULT_SETTINGS[section]:
                return False, f"Unknown setting '{section}/{key}'"
        if section == "security" and "network_binding" in updates:
            if updates["network_binding"] not in ("127.0.0.1", "localhost", "::1"):
                return False, "network_binding change requires explicit confirmation flag confirm_exposure=true"
        if section == "model" and "context_length" in updates:
            v = updates["context_length"]
            if not isinstance(v, int) or not (256 <= v <= 1_000_000):
                return False, "context_length must be an integer between 256 and 1000000"
        return True, None

    def update(self, section: str, updates: Dict[str, Any], actor: str = "user",
               confirm_exposure: bool = False) -> Dict[str, Any]:
        ok, err = self.validate(section, updates)
        if not ok:
            raise ValueError(err)
        if section == "security" and updates.get("network_binding") not in (None, "127.0.0.1", "localhost", "::1") \
                and not confirm_exposure:
            raise ValueError("Changing network exposure requires explicit confirmation.")
        current = self.get_section(section)
        merged = {**current, **updates}
        row = self.db.get(Setting, section)
        if row is None:
            row = Setting(key=section, value={"value": merged})
            self.db.add(row)
        else:
            row.value = {"value": merged}
        self.db.commit()
        if section in SECURITY_RELEVANT_SECTIONS:
            log_audit_event(self.db, actor=actor, action=f"settings.update.{section}",
                            target=section, outcome="success",
                            details={"keys": sorted(updates.keys())})
        return merged

    def restore_defaults(self, section: Optional[str] = None, actor: str = "user"):
        query = self.db.query(Setting)
        if section:
            query = query.filter_by(key=section)
        query.delete(synchronize_session=False)
        self.db.commit()
        log_audit_event(self.db, actor=actor, action="settings.restore_defaults",
                        target=section or "all", outcome="success")
        return self.get_all() if not section else self.get_section(section)

    def export_settings(self) -> str:
        return json.dumps(self.get_all(), indent=2, default=str)

    def import_settings(self, payload: Dict[str, Any], actor: str = "user") -> Dict[str, str]:
        results = {}
        for section, values in payload.items():
            if not isinstance(values, dict):
                results[section] = "skipped (not an object)"
                continue
            try:
                self.update(section, values, actor=actor)
                results[section] = "updated"
            except ValueError as exc:
                results[section] = f"rejected: {exc}"
        return results

    def set_autonomy_profile(self, profile: str, actor: str = "user") -> Dict[str, Any]:
        if profile not in AUTONOMY_PROFILES:
            raise ValueError(f"Unknown autonomy profile '{profile}'")
        # Profiles are convenience presets layered on top of the policy engine;
        # they can never weaken a hard BLOCK.
        overrides = dict(AUTONOMY_PROFILES[profile]["policy_overrides"])
        overrides["system.modify"] = "BLOCK"
        self.update("selfx", {}, actor=actor)  # touch to validate section exists
        row = self.db.get(Setting, "autonomy")
        val = {"profile": profile, "policy_overrides": overrides}
        if row is None:
            row = Setting(key="autonomy", value=val)
            self.db.add(row)
        else:
            row.value = val
        self.db.commit()
        log_audit_event(self.db, actor=actor, action="settings.autonomy_profile",
                        target=profile, outcome="success")
        return val

    def get_autonomy_profile(self) -> Dict[str, Any]:
        row = self.db.get(Setting, "autonomy")
        if row:
            return row.value
        return {"profile": "Supervised Mode",
                "policy_overrides": AUTONOMY_PROFILES["Supervised Mode"]["policy_overrides"]}
