# Chapter 1: Database Models



 library system that tracks books (title, author, ISBN), users (name, email, type), and borrowings (who borrowed which book and when) using structured **database models**.

## What are Database Models?

Database models are the **blueprints for your database**. They define:

1. Tables (e.g., `books`, `users`, `issues`)
2. Columns (e.g., `title`, `author`, `email`)
3. Data types (e.g., text, number, date)
4. Relationships (e.g., linking issues to books and users)

We use **SQLAlchemy** to define these models in Python.

## Model Essentials

### Base Class

Every model inherits from `Base`, defined in `app/database.py`:

```python
from sqlalchemy.orm import declarative_base
Base = declarative_base()
```

### Table Name

Use `__tablename__` to name your table:

```python
__tablename__ = "books"
```

### Columns

Define table fields using `Column`, specifying type and constraints:

```python
id = Column(Integer, primary_key=True, index=True)
title = Column(String(255), nullable=False)
```

**Common SQLAlchemy Types:**

| Type        | Meaning                  |
| ----------- | ------------------------ |
| `Integer`   | Whole numbers            |
| `String(n)` | Text up to length `n`    |
| `Text`      | Long text                |
| `DateTime`  | Date and time            |
| `Boolean`   | True/False               |
| `Enum`      | Predefined set of values |

**Constraints:**

| Constraint         | Description                 |
| ------------------ | --------------------------- |
| `primary_key=True` | Uniquely identifies rows    |
| `nullable=False`   | Value must be present       |
| `unique=True`      | No duplicates allowed       |
| `default=value`    | Sets default if no input    |
| `index=True`       | Speeds up search operations |

### Foreign Keys

Foreign keys link one table to another:

```python
book_id = Column(Integer, ForeignKey("books.id"))
```

### Relationships

Define object-level relations using `relationship`:

```python
book = relationship("Book", back_populates="issues")
```

Ensure you mirror this in the related model:

```python
issues = relationship("Issue", back_populates="book")
```

## Example: User Model

```python
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_type = Column(Enum(UserType), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    phone = Column(String(15))
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    student = relationship("Student", back_populates="user", uselist=False)
    employee = relationship("Employee", back_populates="user", uselist=False)
```

## Creating Tables

Defining models alone doesn't create tables. Use:

```python
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

This uses the collected `Base.metadata` to instruct the database to create tables.

# Chapter 2: Data Schemas (Pydantic)

when data moves *in or out* of the system—say via API requests—we need **schemas** to define the format of this data. That’s where **Pydantic** comes in.

## What are Data Schemas?

Schemas act as **standardized forms** for data transfer. They define what data must be sent or received, and in what format—ensuring a consistent contract between API and client.

For example:
- When creating a book, what fields are required?
- When fetching a book, what does the response look like?

In `netenrich`, we define schemas using **Pydantic**.

## Why Pydantic?

Pydantic offers:

1. **Validation** – Ensures incoming data matches expected types.
2. **Serialization** – Converts SQLAlchemy models to JSON easily.
3. **Documentation** – FastAPI auto-generates Swagger docs using schemas.

## Schema Basics: `BaseModel`

All schemas inherit from `pydantic.BaseModel`. Here's a basic example:

```python
# app/schemas/book.py
from pydantic import BaseModel
from typing import Optional

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

from datetime import datetime
from pydantic import ConfigDict

class BookResponse(BookBase):
    id: int
    available_copies: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

sequenceDiagram
    User->>FastAPI: Send JSON for new book
    FastAPI->>Pydantic: Validate against BookCreate
    Pydantic-->>FastAPI: Return validated object (or error)
    FastAPI->>AppCode: Pass validated object
    AppCode->>Database: Save using SQLAlchemy
    Database-->>AppCode: Return saved model
    AppCode->>Pydantic: Convert to BookResponse
    Pydantic-->>AppCode: Return schema
    AppCode-->>FastAPI: Return response
    FastAPI->>User: Send JSON response




