import datetime
import enum
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum as SQLEnum, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    TIMED_OUT = "TIMED_OUT"
    NEEDS_INPUT = "NEEDS_INPUT"


class ApprovalDecision(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# 1. users
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 2. sessions
class Session(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)

# 3. settings
class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 4. projects
class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 5. tasks
class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), default="medium")
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.CREATED, index=True)
    due_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, index=True)
    category: Mapped[Optional[str]] = mapped_column(String(64))
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    completion_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 6. task_dependencies
class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))
    depends_on_task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"))

# 7. calendar_events
class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False)
    time_zone: Mapped[str] = mapped_column(String(64), default="UTC")
    recurrence_rule: Mapped[Optional[str]] = mapped_column(String(128))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)

# 8. notes
class Note(Base):
    __tablename__ = "notes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    backlinks: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 9. documents
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filepath: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer)
    mime_type: Mapped[Optional[str]] = mapped_column(String(128))
    last_modified: Mapped[datetime.datetime] = mapped_column(DateTime)
    indexing_status: Mapped[str] = mapped_column(String(32), default="pending")
    indexing_error: Mapped[Optional[str]] = mapped_column(Text)
    indexed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

# 10. document_chunks
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

# 11. conversations
class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), default="New Conversation")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 12. messages
class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False) # user, assistant, system, tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    execution_context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 13. memories
class Memory(Base):
    __tablename__ = "memories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    provenance: Mapped[Optional[str]] = mapped_column(String(256))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

# 14. memory_revisions
class MemoryRevision(Base):
    __tablename__ = "memory_revisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    memory_id: Mapped[int] = mapped_column(ForeignKey("memories.id", ondelete="CASCADE"), nullable=False)
    old_value: Mapped[str] = mapped_column(Text, nullable=False)
    new_value: Mapped[str] = mapped_column(Text, nullable=False)
    revised_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 15. agent_runs
class AgentRun(Base):
    __tablename__ = "agent_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.CREATED, index=True)
    plan: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    results: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

# 16. agent_steps
class AgentStep(Base):
    __tablename__ = "agent_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    result: Mapped[Optional[str]] = mapped_column(Text)

# 17. tool_calls
class ToolCall(Base):
    __tablename__ = "tool_calls"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False)
    inputs: Mapped[Dict[str, Any]] = mapped_column(JSON)
    outputs: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 18. approvals
class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    agent_run_id: Mapped[str] = mapped_column(ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision: Mapped[ApprovalDecision] = mapped_column(SQLEnum(ApprovalDecision), default=ApprovalDecision.PENDING, index=True)
    decided_by: Mapped[Optional[str]] = mapped_column(String(64))
    decided_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

# 19. skills
class Skill(Base):
    __tablename__ = "skills"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    current_version: Mapped[str] = mapped_column(String(32), default="1.0.0")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 20. skill_versions
class SkillVersion(Base):
    __tablename__ = "skill_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    manifest: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    provenance: Mapped[Optional[str]] = mapped_column(String(256))
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 21. skill_tests
class SkillTest(Base):
    __tablename__ = "skill_tests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    test_name: Mapped[str] = mapped_column(String(128), nullable=False)
    test_input: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected_output: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    last_passed: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

# 22. research_jobs
class ResearchJob(Base):
    __tablename__ = "research_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    topic: Mapped[str] = mapped_column(String(256), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    findings: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 23. research_sources
class ResearchSource(Base):
    __tablename__ = "research_sources"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    research_job_id: Mapped[str] = mapped_column(ForeignKey("research_jobs.id", ondelete="CASCADE"), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(256))
    excerpt: Mapped[Optional[str]] = mapped_column(Text)
    retrieved_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 24. selfx_goals
class SelfXGoal(Base):
    __tablename__ = "selfx_goals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    baseline: Mapped[Dict[str, Any]] = mapped_column(JSON)
    target: Mapped[Dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 25. evaluations
class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    suite_name: Mapped[str] = mapped_column(String(128), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    results: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 26. improvement_proposals
class ImprovementProposal(Base):
    __tablename__ = "improvement_proposals"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    expected_benefit: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="low")
    status: Mapped[str] = mapped_column(String(32), default="proposed")
    patch_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 27. checkpoints
class Checkpoint(Base):
    __tablename__ = "checkpoints"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_refs: Mapped[Dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 28. scheduled_jobs
class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)

# 29. job_events
class JobEvent(Base):
    __tablename__ = "job_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    details: Mapped[Dict[str, Any]] = mapped_column(JSON)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 30. integrations
class Integration(Base):
    __tablename__ = "integrations"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[Dict[str, Any]] = mapped_column(JSON)
    health_status: Mapped[str] = mapped_column(String(32), default="unknown")

# 31. audit_events
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target: Mapped[Optional[str]] = mapped_column(String(256))
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, index=True)

# 32. notifications
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(32), default="info")
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)

# 33. backup_records
class BackupRecord(Base):
    __tablename__ = "backup_records"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    filepath: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow)
