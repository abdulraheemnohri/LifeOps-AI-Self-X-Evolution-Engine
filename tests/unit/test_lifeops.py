import pytest
import datetime
from src.lifeops.storage.database import get_engine, init_db, get_session_factory
from src.lifeops.storage.models import TaskStatus
from src.lifeops.lifeops.tasks import TaskService, DailyPlannerEngine, NotificationService

def test_task_service_and_daily_planner(tmp_path):
    db_path = tmp_path / "test.db"
    engine = get_engine(f"sqlite:///{db_path}")
    init_db(engine)
    session_factory = get_session_factory(engine)
    db = session_factory()

    task_svc = TaskService(db)
    t1 = task_svc.create_task(title="High Priority Task", priority="high")
    t2 = task_svc.create_task(title="Low Priority Task", priority="low")

    assert t1.id is not None
    assert t1.status == TaskStatus.CREATED

    tasks = task_svc.list_tasks(status=TaskStatus.CREATED)
    assert len(tasks) == 2

    task_svc.update_task_status(t1.id, TaskStatus.SUCCEEDED, completion_notes="Done fast")
    assert task_svc.list_tasks(status=TaskStatus.SUCCEEDED)[0].completion_notes == "Done fast"

    planner = DailyPlannerEngine(db)
    plan = planner.generate_daily_plan()
    assert plan["recommended_tasks"][0]["title"] == "Low Priority Task"

    notif_svc = NotificationService(db)
    n = notif_svc.send_notification("Test Alert", "Remember to drink water")
    assert n.id is not None
    assert len(notif_svc.get_unread()) == 1
    db.close()
