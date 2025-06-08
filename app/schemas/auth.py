from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime
from app.auth.model import UserType


class UserBase(BaseModel):
    email: str
    name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    user_type: UserType


class UserResponse(UserBase):
    id: int
    user_type: UserType
    is_active: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentCreate(BaseModel):
    roll_no: str
    department: str
    semester: int


class StudentResponse(BaseModel):
    user_id: int
    roll_no: str
    department: str
    semester: int
    # Include user details directly instead of nested relationship
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class EmployeeCreate(BaseModel):
    employee_id: str
    department: str
    designation: str
    salary: float


class EmployeeResponse(BaseModel):
    user_id: int
    employee_id: str
    department: str
    designation: str
    salary: float
    # Include user details directly instead of nested relationship
    user: UserResponse

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


# Alternative schemas that don't include user relationship
# Use these if you want to avoid the relationship loading issue
class StudentResponseSimple(BaseModel):
    user_id: int
    roll_no: str
    department: str
    semester: int

    model_config = ConfigDict(from_attributes=True)


class EmployeeResponseSimple(BaseModel):
    user_id: int
    employee_id: str
    department: str
    designation: str
    salary: float

    model_config = ConfigDict(from_attributes=True)
