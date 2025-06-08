from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, distinct
from sqlalchemy.orm import joinedload
from fastapi import HTTPException, status
from typing import Optional, List
from app.books.model import Book
from app.schemas.book import BookCreate, BookUpdate
from app.issues.model import Issue


class BookService:

    @staticmethod
    async def create_book(db: AsyncSession, book_data: BookCreate) -> Book:
        # Check if ISBN already exists
        result = await db.execute(select(Book).where(Book.isbn == book_data.isbn))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Book with this ISBN already exists",
            )

        db_book = Book(
            title=book_data.title,
            author=book_data.author,
            isbn=book_data.isbn,
            total_copies=book_data.total_copies,
            available_copies=book_data.total_copies,
            category=book_data.category,
            description=book_data.description,
        )

        db.add(db_book)
        await db.commit()
        await db.refresh(db_book)
        return db_book

    @staticmethod
    async def get_book_by_id(db: AsyncSession, book_id: int) -> Optional[Book]:
        result = await db.execute(select(Book).where(Book.id == book_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_book(
        db: AsyncSession, book_id: int, book_data: BookUpdate
    ) -> Optional[Book]:
        result = await db.execute(select(Book).where(Book.id == book_id))
        db_book = result.scalar_one_or_none()

        if not db_book:
            return None

        update_data = book_data.model_dump(exclude_unset=True)

        # If total_copies is being updated, adjust available_copies proportionally
        if "total_copies" in update_data:
            old_total = db_book.total_copies
            new_total = update_data["total_copies"]
            issued_copies = old_total - db_book.available_copies

            if new_total < issued_copies:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot reduce total copies below {issued_copies} (currently issued copies)",
                )

            update_data["available_copies"] = new_total - issued_copies

        for field, value in update_data.items():
            setattr(db_book, field, value)

        await db.commit()
        await db.refresh(db_book)
        return db_book

    @staticmethod
    async def delete_book(db: AsyncSession, book_id: int) -> bool:
        result = await db.execute(select(Book).where(Book.id == book_id))
        db_book = result.scalar_one_or_none()

        if not db_book:
            return False

        # Check if book has any active issues
        if db_book.available_copies < db_book.total_copies:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete book with active issues",
            )

        await db.delete(db_book)
        await db.commit()
        return True

    @staticmethod
    async def search_books(
        db: AsyncSession,
        title: Optional[str] = None,
        author: Optional[str] = None,
        category: Optional[str] = None,
        isbn: Optional[str] = None,
        available_only: bool = False,
        page: int = 1,
        limit: int = 10,
    ) -> tuple[List[Book], int]:
        query = select(Book)

        # Apply filters
        conditions = []
        if title:
            conditions.append(Book.title.ilike(f"%{title}%"))
        if author:
            conditions.append(Book.author.ilike(f"%{author}%"))
        if category:
            conditions.append(Book.category.ilike(f"%{category}%"))
        if isbn:
            conditions.append(Book.isbn.ilike(f"%{isbn}%"))
        if available_only:
            conditions.append(Book.available_copies > 0)

        if conditions:
            query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count(Book.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        books = result.scalars().all()

        return list(books), total

    @staticmethod
    async def get_all_categories(db: AsyncSession) -> List[str]:
        """
        Get all unique book categories from the database.
        Returns a sorted list of non-null, non-empty categories.
        """
        try:
            query = (
                select(distinct(Book.category))
                .where(and_(Book.category.is_not(None), Book.category != ""))
                .order_by(Book.category)
            )

            result = await db.execute(query)
            categories = result.scalars().all()

            # Filter out any None values and empty strings that might have slipped through
            categories = [cat for cat in categories if cat and cat.strip()]

            return sorted(list(set(categories)))  # Remove duplicates and sort
        except Exception as e:
            # Log the error in a real application
            print(f"Error fetching categories: {e}")
            return []

    @staticmethod
    async def get_all_authors(db: AsyncSession) -> List[str]:
        """
        Get all unique book authors from the database.
        Returns a sorted list of non-null, non-empty authors.
        """
        try:
            query = (
                select(distinct(Book.author))
                .where(and_(Book.author.is_not(None), Book.author != ""))
                .order_by(Book.author)
            )

            result = await db.execute(query)
            authors = result.scalars().all()

            # Filter out any None values and empty strings that might have slipped through
            authors = [author for author in authors if author and author.strip()]

            return sorted(list(set(authors)))  # Remove duplicates and sort
        except Exception as e:
            # Log the error in a real application
            print(f"Error fetching authors: {e}")
            return []

    @staticmethod
    async def set_book_availability(
        db: AsyncSession, book_id: int, available: bool
    ) -> Optional[Book]:
        """
        Set book availability status. This is different from deleting -
        it's used for temporarily making books unavailable.

        Note: This assumes your Book model has an 'is_available' field.
        If not, you might need to add this field to your model.

        Args:
            db: Database session
            book_id: ID of the book to update
            available: True to make available, False to make unavailable

        Returns:
            Updated book object or None if book not found
        """
        try:
            result = await db.execute(select(Book).where(Book.id == book_id))
            db_book = result.scalar_one_or_none()

            if not db_book:
                return None

            # If your Book model has an 'is_available' field:
            # db_book.is_available = available

            # Alternative: If you don't have is_available field,
            # you could use available_copies to simulate availability
            if not available:
                # Store current available copies and set to 0
                if not hasattr(db_book, "_original_available_copies"):
                    db_book._original_available_copies = db_book.available_copies
                db_book.available_copies = 0
            else:
                # Restore original available copies
                if hasattr(db_book, "_original_available_copies"):
                    db_book.available_copies = db_book._original_available_copies
                    delattr(db_book, "_original_available_copies")
                else:
                    # If we don't have original count, assume all copies are available
                    db_book.available_copies = db_book.total_copies

            await db.commit()
            await db.refresh(db_book)
            return db_book

        except Exception as e:
            await db.rollback()
            print(f"Error setting book availability: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update book availability",
            )

    @staticmethod
    async def get_books_by_availability(
        db: AsyncSession, available_only: bool = True
    ) -> List[Book]:
        """
        Get books based on availability status.

        Args:
            db: Database session
            available_only: If True, return only available books. If False, return all books.

        Returns:
            List of books matching the availability criteria
        """
        try:
            query = select(Book)

            if available_only:
                query = query.where(Book.available_copies > 0)

            result = await db.execute(query)
            books = result.scalars().all()

            return list(books)

        except Exception as e:
            print(f"Error fetching books by availability: {e}")
            return []

    @staticmethod
    async def get_book_stats(db: AsyncSession) -> dict:
        """
        Get statistics about the book collection.

        Returns:
            Dictionary containing various statistics about books
        """
        try:
            # Total books
            total_books_result = await db.execute(select(func.count(Book.id)))
            total_books = total_books_result.scalar()

            # Available books
            available_books_result = await db.execute(
                select(func.count(Book.id)).where(Book.available_copies > 0)
            )
            available_books = available_books_result.scalar()

            # Total copies
            total_copies_result = await db.execute(select(func.sum(Book.total_copies)))
            total_copies = total_copies_result.scalar() or 0

            # Available copies
            available_copies_result = await db.execute(
                select(func.sum(Book.available_copies))
            )
            available_copies = available_copies_result.scalar() or 0

            # Total categories
            categories_result = await db.execute(
                select(func.count(distinct(Book.category))).where(
                    and_(Book.category.is_not(None), Book.category != "")
                )
            )
            total_categories = categories_result.scalar()

            # Total authors
            authors_result = await db.execute(
                select(func.count(distinct(Book.author))).where(
                    and_(Book.author.is_not(None), Book.author != "")
                )
            )
            total_authors = authors_result.scalar()

            return {
                "total_books": total_books,
                "available_books": available_books,
                "unavailable_books": total_books - available_books,
                "total_copies": total_copies,
                "available_copies": available_copies,
                "issued_copies": total_copies - available_copies,
                "total_categories": total_categories,
                "total_authors": total_authors,
                "availability_percentage": (
                    (available_copies / total_copies * 100) if total_copies > 0 else 0
                ),
            }

        except Exception as e:
            print(f"Error fetching book stats: {e}")
            return {
                "total_books": 0,
                "available_books": 0,
                "unavailable_books": 0,
                "total_copies": 0,
                "available_copies": 0,
                "issued_copies": 0,
                "total_categories": 0,
                "total_authors": 0,
                "availability_percentage": 0,
            }

    @staticmethod
    async def get_books_by_user(db: AsyncSession, user_id: int):
        try:
            result = await db.execute(
                select(Book)
                .join(Issue, Book.id == Issue.book_id)
                .where(Issue.student_id == user_id)
                .options(
                    joinedload(Book.issues)
                )  # Optional, if you want issue details loaded
            )
            books = result.scalars().all()
            return books
        except Exception as e:
            print(f"Error in get_books_by_user: {e}")
            raise
