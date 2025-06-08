from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.database import create_tables
from app.auth.controller import router as auth_router
from app.books.controller import router as books_router
from app.issues.controller import router as issues_router
from app.students.controller import router as students_router
from app.scheduler.service import SchedulerService
from app.notifications.controller import router as notifications_router
import logging

# Configure logging
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables first
    await create_tables()
    logger.info("Database tables created")

    # Start scheduler
    SchedulerService.start_scheduler()
    logger.info("Scheduler service started")

    yield

    # Shutdown scheduler on exit
    scheduler = SchedulerService.get_scheduler()
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler service stopped")


app = FastAPI(
    title="lib.ai",
    description="A comprehensive library management system API - powered by GEMINI AI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router)
app.include_router(books_router)
app.include_router(issues_router)
app.include_router(students_router)
app.include_router(notifications_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the lib.ai API! Visit /docs for documentation.",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
async def health_check():
    # Basic scheduler health check
    scheduler = SchedulerService.get_scheduler()
    scheduler_status = "running" if scheduler and scheduler.running else "stopped"

    return {
        "status": "healthy",
        "message": "lib.ai API is running smoothly!",
        "scheduler": scheduler_status,
        "jobs": len(scheduler.get_jobs()) if scheduler else 0,
    }
