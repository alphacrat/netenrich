from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_database
from app.notifications.model import Notification
from app.schemas.notification import (
    NotificationResponse,
    NotificationCreate,
    NotificationUpdate,
)
from datetime import datetime

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
    skip: int = 0,
    limit: int = 100,
    student_id: int = None,
    is_read: bool = None,
    notification_type: str = None,
    db: Session = Depends(get_database),
):
    """Get notifications with optional filters"""
    query = db.query(Notification)

    if student_id:
        query = query.filter(Notification.student_id == student_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    if notification_type:
        query = query.filter(Notification.type == notification_type)

    notifications = (
        query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
    )
    return notifications


@router.get("/{notification_id}", response_model=NotificationResponse)
def get_notification(notification_id: int, db: Session = Depends(get_database)):
    """Get a specific notification"""
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )
    return notification


@router.post("/", response_model=NotificationResponse)
def create_notification(
    notification: NotificationCreate, db: Session = Depends(get_database)
):
    """Create a new notification"""
    db_notification = Notification(
        student_id=notification.student_id,
        message=notification.message,
        type=notification.type,
        created_at=datetime.utcnow(),
        is_read=False,
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification


@router.put("/{notification_id}", response_model=NotificationResponse)
def update_notification(
    notification_id: int,
    notification_update: NotificationUpdate,
    db: Session = Depends(get_database),
):
    """Update a notification (mainly for marking as read)"""
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    if notification_update.is_read is not None:
        notification.is_read = notification_update.is_read

    db.commit()
    db.refresh(notification)
    return notification


@router.put("/student/{student_id}/mark-all-read")
def mark_all_read_for_student(student_id: int, db: Session = Depends(get_database)):
    """Mark all notifications as read for a specific student"""
    updated = (
        db.query(Notification)
        .filter(Notification.student_id == student_id, Notification.is_read == False)
        .update({"is_read": True})
    )

    db.commit()
    return {"message": f"Marked {updated} notifications as read"}


@router.delete("/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_database)):
    """Delete a notification"""
    notification = (
        db.query(Notification).filter(Notification.id == notification_id).first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found"
        )

    db.delete(notification)
    db.commit()
    return {"message": "Notification deleted successfully"}


@router.get("/student/{student_id}/unread-count")
def get_unread_count(student_id: int, db: Session = Depends(get_database)):
    """Get count of unread notifications for a student"""
    count = (
        db.query(Notification)
        .filter(Notification.student_id == student_id, Notification.is_read == False)
        .count()
    )

    return {"unread_count": count}
