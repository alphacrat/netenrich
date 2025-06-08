from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Date,
    DECIMAL,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

import enum


class UserType(str, enum.Enum):
    STUDENT = "student"
    ADMIN = "admin"
    LIBRARIAN = "librarian"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_type = Column(Enum(UserType), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(15), nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    student = relationship("Student", back_populates="user", uselist=False)
    employee = relationship("Employee", back_populates="user", uselist=False)


class Student(Base):
    __tablename__ = "students"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    roll_no = Column(String(20), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False)
    semester = Column(Integer, nullable=False)

    # Relationships
    user = relationship("User", back_populates="student")
    issues = relationship(
        "Issue", back_populates="student", cascade="all, delete-orphan"
    )
    notifications = relationship("Notification", back_populates="student")


class Employee(Base):
    __tablename__ = "employees"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    employee_id = Column(String(20), unique=True, nullable=False, index=True)
    department = Column(String(100), nullable=False)
    designation = Column(String(100), nullable=False)
    salary = Column(DECIMAL(10, 2), nullable=False)

    # Relationships
    user = relationship("User", back_populates="employee")
