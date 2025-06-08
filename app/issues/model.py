from sqlalchemy import Column, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.user_id"), nullable=False)
    issue_date = Column(DateTime(timezone=True), server_default=func.now())
    due_date = Column(DateTime(timezone=True), nullable=False)
    return_date = Column(DateTime(timezone=True), nullable=True)
    is_returned = Column(Boolean, default=False)
    overdue_notices_sent = Column(Integer, default=0)
    last_notice_sent = Column(DateTime, nullable=True)

    # Relationships
    book = relationship("Book", back_populates="issues")
    student = relationship("Student", back_populates="issues")
