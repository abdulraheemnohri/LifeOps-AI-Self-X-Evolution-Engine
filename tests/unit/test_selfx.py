import pytest
from src.lifeops.storage.database import get_engine, init_db, get_session_factory
from src.lifeops.selfx.engine import (
    SelfIdentity, SelfDiagnostics, SelfSkills, SelfMemory, SelfRecovery, ImprovementManager
)

def test_selfx_modules(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    # Identity
    ident = SelfIdentity.get_system_identity()
    assert ident["app_name"] == "LifeOps AI + Self-X Evolution Engine"

    # Diagnostics
    diag = SelfDiagnostics(db)
    hc = diag.run_health_check()
    assert hc["status"] == "healthy"

    # Skills
    skills_mgr = SelfSkills(db)
    skill = skills_mgr.draft_skill("file_summarizer", "Summarizer", "Summarize text", "Instruction details", {"tools": ["filesystem"]})
    assert skill.id == "file_summarizer"

    # Memory
    mem_mgr = SelfMemory(db)
    m1 = mem_mgr.store_memory("user_pref", "theme", "dark", provenance="user setting")
    assert m1.value == "dark"
    m2 = mem_mgr.store_memory("user_pref", "theme", "light")
    assert m2.value == "light"
    mems = mem_mgr.retrieve_memories("user_pref")
    assert len(mems) == 1
    assert mems[0].value == "light"

    # Recovery Checkpoint
    rec_mgr = SelfRecovery(db)
    cp = rec_mgr.create_checkpoint("Pre-migration backup", {"db": "test.db"})
    assert cp.id.startswith("cp_")

    # Improvement Manager
    imp_mgr = ImprovementManager(db)
    prop = imp_mgr.propose_improvement("Slow query in task search", "Add index on tags", "low")
    assert prop.id.startswith("imp_")
    db.close()
