import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from src.lifeops.storage.models import Task, Project, CalendarEvent, Note, Document, TaskStatus, Notification

class TaskService:
    def __init__(self, db: DBSession):
        self.db = db

    def create_task(self, title: str, description: Optional[str] = None, priority: str = "medium",
                    due_date: Optional[datetime.datetime] = None, category: Optional[str] = None,
                    tags: Optional[List[str]] = None, project_id: Optional[int] = None) -> Task:
        task = Task(
            title=title,
            description=description,
            priority=priority,
            due_date=due_date,
            category=category,
            tags=tags or [],
            project_id=project_id,
            status=TaskStatus.CREATED
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(self, status: Optional[TaskStatus] = None, project_id: Optional[int] = None) -> List[Task]:
        query = self.db.query(Task)
        if status:
            query = query.filter(Task.status == status)
        if project_id:
            query = query.filter(Task.project_id == project_id)
        return query.all()

    def update_task_status(self, task_id: int, status: TaskStatus, completion_notes: Optional[str] = None) -> Optional[Task]:
        task = self.db.query(Task).filter_by(id=task_id).first()
        if not task:
            return None
        task.status = status
        if completion_notes:
            task.completion_notes = completion_notes
        self.db.commit()
        self.db.refresh(task)
        return task

class DailyPlannerEngine:
    def __init__(self, db: DBSession):
        self.db = db

    def generate_daily_plan(self, date: Optional[datetime.date] = None) -> Dict[str, Any]:
        if date is None:
            date = datetime.date.today()

        # Fetch pending tasks and events
        tasks = self.db.query(Task).filter(Task.status.in_([TaskStatus.CREATED, TaskStatus.QUEUED])).all()
        start_of_day = datetime.datetime.combine(date, datetime.time.min)
        end_of_day = datetime.datetime.combine(date, datetime.time.max)
        events = self.db.query(CalendarEvent).filter(
            CalendarEvent.start_time >= start_of_day,
            CalendarEvent.start_time <= end_of_day
        ).all()

        prioritized_tasks = sorted(tasks, key=lambda t: (0 if t.priority == "high" else 1 if t.priority == "medium" else 2))

        plan = {
            "date": str(date),
            "scheduled_events": [{"title": e.title, "start": str(e.start_time), "end": str(e.end_time)} for e in events],
            "recommended_tasks": [{"id": t.id, "title": t.title, "priority": t.priority} for t in prioritized_tasks[:5]],
            "estimated_duration_hours": len(prioritized_tasks[:5]) * 1.0
        }
        return plan

class NotificationService:
    def __init__(self, db: DBSession):
        self.db = db

    def send_notification(self, title: str, message: str, level: str = "info") -> Notification:
        notif = Notification(title=title, message=message, level=level)
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def get_unread(self) -> List[Notification]:
        return self.db.query(Notification).filter_by(read=False).all()
