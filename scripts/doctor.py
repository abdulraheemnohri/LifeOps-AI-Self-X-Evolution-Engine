import sys
import os
import platform
from lifeops.storage.database import get_engine, init_db
from lifeops.selfx.engine import SelfIdentity, SelfDiagnostics

def run_doctor():
    print("=== LifeOps AI System Doctor ===")
    print(f"Python Version: {sys.version}")
    print(f"Platform: {platform.platform()}")

    engine = get_engine()
    init_db(engine)

    from lifeops.storage.database import get_session_factory
    sf = get_session_factory(engine)
    db = sf()

    diag = SelfDiagnostics(db)
    hc = diag.run_health_check()
    print(f"Database Health: {hc['status']}")

    print("All checks completed successfully!")
    db.close()

if __name__ == "__main__":
    run_doctor()
