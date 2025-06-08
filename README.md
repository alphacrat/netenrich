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


# Chapter 3: AI Assistant

The `lib.ai` system integrates an AI-powered assistant using the `/chat` API routes. This assistant leverages a custom `ChatService` to interpret user queries and provide intelligent responses based on library data.

## Endpoints

### POST `/chat/`

A non-streaming endpoint for handling a single user message and returning an AI-generated reply.

```json
{
  "message": "How many books are overdue?",
  "session_id": "abc123"
}
```

### POST `/chat/stream`

Streams the AI-generated response word-by-word for real-time feedback.

### GET `/chat/history/{session_id}`

Fetches the conversation history of a particular session.

### DELETE `/chat/history/{session_id}`

Clears the stored conversation context of a session.

### GET `/chat/test`

Runs a few predefined test queries to verify the AI assistant's functionality.

> **Note:** In production, replace in-memory session storage with Redis or a database.

---

# Chapter 4: Environment Setup (`.env` File)

To run the system properly, set the following environment variables in a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://clouddb(add own)/defaultdb

SECRET_KEY=add_the_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=30

SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
EMAIL_FROM=your_email@gmail.com
EMAIL_FROM_NAME=Library Notification System
```

These are used for:

* Connecting to the database
* Generating and verifying JWT tokens
* Sending notification emails

---

# Chapter 5: Running the Application

To run the `lib.ai` application:

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Environment Variables

Create a `.env` file as shown in Chapter 4.

## Step 3: Launch the FastAPI Server

```bash
uvicorn main:app --reload
```

## Server Features

* Automatically creates database tables using `create_tables()`
* Starts a background scheduler using `SchedulerService`
* Includes routers for:

  * Authentication
  * Books
  * Issues
  * Students
  * Notifications
  * AI Assistant (`/chat`)

## Available Routes

* `/docs` – Swagger UI for interactive API docs
* `/health` – API and scheduler health check

---

These chapters document the database, schema, AI assistant integration, environment setup, and application launch process in `lib.ai`.

Visit:

- [http://localhost:8000/docs](http://localhost:8000/docs) for interactive **Swagger API documentation**.

- [http://localhost:8000/redoc](http://localhost:8000/redoc) for ReDoc documentation.

- [http://localhost:8000/health](http://localhost:8000/health) for a health check endpoint.



