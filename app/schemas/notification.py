from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


class NotificationBase(BaseModel):
    student_id: int
    message: str
    type: str


class NotificationCreate(NotificationBase):
    pass


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None


class NotificationResponse(NotificationBase):
    id: int
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True


class EmailSchema(BaseModel):
    email: List[str]
    subject: str
    body: str
