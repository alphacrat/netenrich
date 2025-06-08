from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class IssueCreate(BaseModel):
    book_id: int
    student_id: int
    days_to_return: Optional[int] = 14


class IssueResponse(BaseModel):
    id: int
    book_id: int
    student_id: int
    issue_date: datetime
    due_date: datetime
    return_date: Optional[datetime] = None
    is_returned: bool

    class Config:
        from_attributes = True


class IssueWithDetails(IssueResponse):
    book_title: str
    book_author: str
    student_name: str
    student_roll_no: str
