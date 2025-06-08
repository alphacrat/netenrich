from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Dict, Any
from app.database import get_database
from app.schemas.book import BookCreate, BookUpdate, BookResponse
from app.schemas.auth import UserResponse
from app.books.service import BookService
from app.core.deps import get_admin_or_librarian, get_current_active_user

router = APIRouter(prefix="/books", tags=["Books"])


@router.post("/", response_model=BookResponse)
async def create_book(
    book_data: BookCreate,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):
    try:
        book = await BookService.create_book(db, book_data)
        return book
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        )


@router.get("/", response_model=dict)
async def search_books(
    title: Optional[str] = Query(None, description="Filter by title"),
    author: Optional[str] = Query(None, description="Filter by author"),
    category: Optional[str] = Query(None, description="Filter by category"),
    isbn: Optional[str] = Query(None, description="Filter by ISBN"),
    available: Optional[bool] = Query(None, description="Only Available Books"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_current_active_user),
):
    try:
        # Fix: Correct parameter order and names
        books, total = await BookService.search_books(
            db=db,
            title=title,
            author=author,
            category=category,
            isbn=isbn,
            available_only=available or False,
            page=page,
            limit=limit,
        )

        # Fix pagination calculation
        total_pages = (total + limit - 1) // limit

        # Convert SQLAlchemy models to dictionaries
        books_data = []
        for book in books:
            books_data.append(
                {
                    "id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "category": book.category,
                    "isbn": book.isbn,
                    "total_copies": book.total_copies,
                    "available_copies": book.available_copies,
                    "created_at": (
                        book.created_at.isoformat() if book.created_at else None
                    ),
                    "updated_at": (
                        book.updated_at.isoformat() if book.updated_at else None
                    ),
                }
            )

        return {
            "books": books_data,
            "pagination": {
                "total": total,
                "page": page,
                "limit": limit,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
            "filters": {
                "title": title,
                "author": author,
                "category": category,
                "isbn": isbn,
                "available": available,
            },
        }
    except Exception as e:
        print(f"Book search error: {e}")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while searching for books",
        )


@router.get("/categories", response_model=List[str])
async def get_book_categories(
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_current_active_user),
):
    try:
        categories = await BookService.get_all_categories(db)
        return categories
    except Exception as e:
        print(f"Error fetching book categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching book categories",
        )


@router.get("/authors", response_model=List[str])
async def get_book_authors(
    db: AsyncSession = Depends(get_database),
    current_user: UserResponse = Depends(get_current_active_user),
):
    try:
        authors = await BookService.get_all_authors(db)
        return authors
    except Exception as e:
        print(f"Get authors error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve authors",
        )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_current_active_user),
):
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid book ID (ID must be +ve integer)",
        )

    try:
        book = await BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Book not found"
            )
        return book
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error fetching book with ID {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while fetching the book",
        )


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_database),
    current_user=Depends(get_admin_or_librarian),
):

    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer",
        )

    try:
        book = await BookService.update_book(db, book_id, book_data)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found",
            )
        return book
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Update book error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book",
        )


@router.delete("/{book_id}")
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_database),
    current_user: UserResponse = Depends(get_admin_or_librarian),
):
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer",
        )
    try:
        success = await BookService.delete_book(db, book_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found",
            )
        return {
            "message": f"Book deleted successfully",
            "book_id": book_id,
            "deleted_by": current_user.email if current_user else "Unknown",
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        print(f"Delete book error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book",
        )


@router.get("/{book_id}/availability", response_model=dict)
async def check_book_availability(
    book_id: int,
    db: AsyncSession = Depends(get_database),
    current_user: UserResponse = Depends(
        get_current_active_user
    ),  # Any authenticated user can check
):
    """
    Check the availability of a specific book.
    Returns total copies, available copies, and availability status.
    """
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer",
        )

    try:
        book = await BookService.get_book_by_id(db, book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found",
            )

        return {
            "book_id": book.id,
            "title": book.title,
            "author": book.author,
            "isbn": book.isbn,
            "total_copies": book.total_copies,
            "available_copies": book.available_copies,
            "issued_copies": book.total_copies - book.available_copies,
            "is_available": book.available_copies > 0,
            "availability_percentage": (
                (book.available_copies / book.total_copies * 100)
                if book.total_copies > 0
                else 0
            ),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Check availability error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check book availability",
        )


# issues must be filled
@router.get("/user/{user_id}", response_model=List[BookResponse])
async def get_books_by_user(
    user_id: int,
    db: AsyncSession = Depends(get_database),
    current_user: UserResponse = Depends(get_current_active_user),
):
    try:
        books = await BookService.get_books_by_user(db, user_id)
        return books
    except Exception as e:
        print(f"Error fetching books by user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve books for the user",
        )
