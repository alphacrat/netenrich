from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class BookBase(BaseModel):
    title: str
    author: str
    isbn: str
    total_copies: int
    category: str
    description: Optional[str] = None


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    isbn: Optional[str] = None
    total_copies: Optional[int] = None
    category: Optional[str] = None
    description: Optional[str] = None


class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
