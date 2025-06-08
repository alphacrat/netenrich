# app/scheduler/service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
from app.database import get_database
from app.issues.service import IssueService
from app.notifications.service import NotificationService
from fastapi import BackgroundTasks
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class SchedulerService:
    _scheduler = None

    @classmethod
    def get_scheduler(cls):
        if cls._scheduler is None:
            cls._scheduler = AsyncIOScheduler()
        return cls._scheduler

    @classmethod
    async def check_overdue_books(cls, db):
        """Check for overdue books and send notifications"""
        try:
            # Get all overdue books
            overdue_issues = await IssueService.get_overdue_books(db)

            # Get books due in next 5 days
            due_soon = await IssueService.get_books_due_soon(db, days=5)

            background_tasks = BackgroundTasks()

            # Send overdue notices
            for issue in overdue_issues:
                days_overdue = (datetime.now() - issue.due_date).days
                await NotificationService.send_overdue_notification(
                    background_tasks, issue, days_overdue
                )

            # Send due soon notices
            for issue in due_soon:
                if not issue.last_notice_sent or (
                    datetime.now() - issue.last_notice_sent
                ) > timedelta(days=1):
                    await NotificationService.send_overdue_notification(
                        background_tasks, issue
                    )
                    # Update last notice sent time
                    issue.last_notice_sent = datetime.now()
                    await db.commit()

            await background_tasks()

        except Exception as e:
            logger.error(f"Error in overdue book check: {e}")

    @classmethod
    def start_scheduler(cls):
        """Start the scheduler"""
        scheduler = cls.get_scheduler()
        if not scheduler.running:
            scheduler.start()
            # Run every 6 hours
            trigger = IntervalTrigger(hours=6)
            scheduler.add_job(
                cls.check_overdue_books, trigger=trigger, args=[get_database()]
            )
            logger.info("Scheduler started")
