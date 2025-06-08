# app/notifications/service.py
from fastapi import BackgroundTasks
from datetime import datetime
from typing import List
from app.config import settings
from app.issues.model import Issue
from app.schemas.notification import EmailSchema
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class NotificationService:

    @staticmethod
    async def send_overdue_notification(
        background_tasks: BackgroundTasks, issue: Issue, days_overdue: int = 0
    ):
        """Send overdue notification email"""
        subject = f"Book Return Reminder: {issue.book.title}"

        if days_overdue > 0:
            body = f"""
            Dear {issue.student.user.name},
            
            The book "{issue.book.title}" by {issue.book.author} is now {days_overdue} days overdue.
            Please return it to the library as soon as possible to avoid penalties.
            
            Original due date: {issue.due_date.strftime('%Y-%m-%d')}
            
            Library Management System
            """
        else:
            days_remaining = (issue.due_date - datetime.now()).days
            body = f"""
            Dear {issue.student.user.name},
            
            This is a friendly reminder that the book "{issue.book.title}" is due in {days_remaining} days.
            Please return it by {issue.due_date.strftime('%Y-%m-%d')}.
            
            Library Management System
            """

        email_data = EmailSchema(
            email=[issue.student.user.email], subject=subject, body=body
        )

        background_tasks.add_task(NotificationService.send_email, email_data)

    @staticmethod
    def send_email(email_data: EmailSchema):
        """Send email using SMTP"""
        try:
            message = MIMEMultipart()
            message["From"] = settings.SMTP_USER
            message["To"] = ", ".join(email_data.email)
            message["Subject"] = email_data.subject

            message.attach(MIMEText(email_data.body, "plain"))

            with smtplib.SMTP(
                host=settings.SMTP_HOST, port=settings.SMTP_PORT
            ) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(message)

            logger.info(f"Email sent to {email_data.email}")
        except Exception as e:
            logger.error(f"Error sending email: {e}")
