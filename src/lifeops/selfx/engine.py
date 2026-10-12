import sys
import platform
import uuid
import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session as DBSession
from src.lifeops.storage.models import (
    Skill, SkillVersion, SkillTest, Memory, MemoryRevision, SelfXGoal, Evaluation,
    ImprovementProposal, Checkpoint
)

class SelfIdentity:
    def __init__(self, db: DBSession):
        self.db = db

    def get_system_identity() -> Dict[str, Any]:
        return {
            "app_name": "LifeOps AI + Self-X Evolution Engine",
            "version": "0.1.0",
            "python_version": sys.version,
            "platform": platform.platform(),
            "capabilities": ["task_management", "memory_indexing", "skill_learning", "self_diagnostics", "recovery"],
        }

class SelfDiagnostics:
    def __init__(self, db: DBSession):
        self.db = db

    def run_health_check(self) -> Dict[str, Any]:
        db_healthy = True
        try:
            self.db.execute(self.db.query(Skill).statement)
        except Exception:
            db_healthy = False

        return {
            "status": "healthy" if db_healthy else "degraded",
            "database_connected": db_healthy,
            "timestamp": str(datetime.datetime.now(datetime.timezone.utc)),
        }

    def diagnose_failed_job(self, job_id: str, error_msg: str) -> Dict[str, Any]:
        return {
            "job_id": job_id,
            "category": "runtime_exception",
            "root_cause_hypothesis": f"Unhandled error: {error_msg}",
            "recommended_action": "Retry with isolated workspace or patch skill manifest",
        }

class SelfSkills:
    def __init__(self, db: DBSession):
        self.db = db

    def draft_skill(self, skill_id: str, name: str, description: str, instructions: str, manifest: Dict[str, Any]) -> Skill:
        skill = self.db.query(Skill).filter_by(id=skill_id).first()
        if not skill:
            skill = Skill(id=skill_id, name=name, description=description, current_version="1.0.0", enabled=True)
            self.db.add(skill)

        version = SkillVersion(
            skill_id=skill_id,
            version="1.0.0",
            instructions=instructions,
            manifest=manifest,
            provenance="Self-X Learner"
        )
        self.db.add(version)
        self.db.commit()
        return skill

    def publish_skill_version(self, skill_id: str, version: str) -> bool:
        skill = self.db.query(Skill).filter_by(id=skill_id).first()
        if skill:
            skill.current_version = version
            self.db.commit()
            return True
        return False

class SelfMemory:
    def __init__(self, db: DBSession):
        self.db = db

    def store_memory(self, category: str, key: str, value: str, provenance: Optional[str] = None) -> Memory:
        mem = self.db.query(Memory).filter_by(category=category, key=key).first()
        if mem:
            rev = MemoryRevision(memory_id=mem.id, old_value=mem.value, new_value=value)
            self.db.add(rev)
            mem.value = value
            if provenance:
                mem.provenance = provenance
        else:
            mem = Memory(category=category, key=key, value=value, provenance=provenance)
            self.db.add(mem)
        self.db.commit()
        self.db.refresh(mem)
        return mem

    def retrieve_memories(self, category: Optional[str] = None) -> List[Memory]:
        query = self.db.query(Memory).filter_by(is_stale=False)
        if category:
            query = query.filter_by(category=category)
        return query.all()

class SelfRecovery:
    def __init__(self, db: DBSession):
        self.db = db

    def create_checkpoint(self, description: str, artifact_refs: Dict[str, Any]) -> Checkpoint:
        cp_id = f"cp_{uuid.uuid4().hex[:12]}"
        cp = Checkpoint(id=cp_id, description=description, artifact_refs=artifact_refs)
        self.db.add(cp)
        self.db.commit()
        self.db.refresh(cp)
        return cp

class ImprovementManager:
    def __init__(self, db: DBSession):
        self.db = db

    def propose_improvement(self, problem: str, expected_benefit: str, risk_level: str = "low", patch_data: Optional[Dict[str, Any]] = None) -> ImprovementProposal:
        prop_id = f"imp_{uuid.uuid4().hex[:12]}"
        prop = ImprovementProposal(
            id=prop_id,
            problem=problem,
            expected_benefit=expected_benefit,
            risk_level=risk_level,
            patch_data=patch_data or {},
            status="proposed"
        )
        self.db.add(prop)
        self.db.commit()
        self.db.refresh(prop)
        return prop
