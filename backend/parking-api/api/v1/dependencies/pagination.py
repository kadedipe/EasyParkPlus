"""
Pagination dependencies for list endpoints.
"""

from typing import Optional, Generic, TypeVar, List, Dict, Any
from math import ceil
from pydantic import BaseModel, Field
from fastapi import Query, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')
DataT = TypeVar('DataT')


class PaginationParams(BaseModel):
    """
    Pagination parameters.
    """
    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Items per page")
    sort: Optional[str] = Field(None, description="Sort field (prefix with - for descending)")
    
    class Config:
        arbitrary_types_allowed = True
    
    @property
    def skip(self) -> int:
        """Calculate skip value."""
        return (self.page - 1) * self.size
    
    @property
    def limit(self) -> int:
        """Get limit value."""
        return self.size
    
    def get_sort_clause(self, model):
        """
        Get SQLAlchemy sort clause.
        """
        if not self.sort:
            return None
        
        if self.sort.startswith('-'):
            field = self.sort[1:]
            return getattr(model, field).desc()
        else:
            return getattr(model, self.sort).asc()


class PaginatedResponse(BaseModel, Generic[DataT]):
    """
    Paginated response model.
    """
    items: List[DataT]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool
    next_page: Optional[int]
    prev_page: Optional[int]
    
    class Config:
        arbitrary_types_allowed = True


async def get_pagination(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: Optional[str] = Query(None, description="Sort field (prefix with - for descending)")
) -> PaginationParams:
    """
    Dependency for getting pagination parameters.
    """
    return PaginationParams(page=page, size=size, sort=sort)


async def paginate_query(
    db: AsyncSession,
    query,
    pagination: PaginationParams,
    count_query=None
) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.
    """
    # Get total count
    if count_query is None:
        count_query = select(func.count()).select_from(query.subquery())
    
    total = await db.scalar(count_query) or 0
    
    # Apply pagination
    if pagination.sort:
        # Apply sorting if specified
        pass  # Sorting handled in query
    
    result = await db.execute(
        query.offset(pagination.skip).limit(pagination.limit)
    )
    items = result.scalars().all()
    
    # Calculate pagination metadata
    pages = ceil(total / pagination.size) if total > 0 else 0
    has_next = pagination.page < pages
    has_prev = pagination.page > 1
    
    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "pages": pages,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_page": pagination.page + 1 if has_next else None,
        "prev_page": pagination.page - 1 if has_prev else None
    }


def paginate(
    items: List[T],
    total: int,
    page: int,
    size: int
) -> PaginatedResponse[T]:
    """
    Create paginated response from items list.
    """
    pages = ceil(total / size) if total > 0 else 0
    has_next = page < pages
    has_prev = page > 1
    
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages,
        has_next=has_next,
        has_prev=has_prev,
        next_page=page + 1 if has_next else None,
        prev_page=page - 1 if has_prev else None
    )


class CursorPaginationParams(BaseModel):
    """
    Cursor-based pagination parameters.
    """
    cursor: Optional[str] = Field(None, description="Pagination cursor")
    limit: int = Field(20, ge=1, le=100, description="Items per page")
    
    @property
    def skip(self) -> int:
        """Calculate skip value."""
        return 0  # Cursor pagination doesn't use skip


async def get_cursor_pagination(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page")
) -> CursorPaginationParams:
    """
    Dependency for getting cursor pagination parameters.
    """
    return CursorPaginationParams(cursor=cursor, limit=limit)


class PageNumberPagination:
    """
    Page number pagination class.
    """
    
    def __init__(self, page_size: int = 20, max_page_size: int = 100):
        self.page_size = page_size
        self.max_page_size = max_page_size
    
    async def paginate_query(self, query, request: Request, db: AsyncSession):
        """
        Paginate query using page numbers.
        """
        # Get pagination parameters
        page = int(request.query_params.get('page', 1))
        size = int(request.query_params.get('size', self.page_size))
        
        # Validate
        if size > self.max_page_size:
            size = self.max_page_size
        
        # Calculate offset
        offset = (page - 1) * size
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0
        
        # Get items
        result = await db.execute(query.offset(offset).limit(size))
        items = result.scalars().all()
        
        # Build response
        return {
            'items': items,
            'total': total,
            'page': page,
            'size': size,
            'pages': ceil(total / size) if total > 0 else 0
        }


class OffsetPagination:
    """
    Offset-based pagination class.
    """
    
    def __init__(self, default_limit: int = 20, max_limit: int = 100):
        self.default_limit = default_limit
        self.max_limit = max_limit
    
    async def paginate_query(self, query, request: Request, db: AsyncSession):
        """
        Paginate query using offset/limit.
        """
        # Get pagination parameters
        offset = int(request.query_params.get('offset', 0))
        limit = int(request.query_params.get('limit', self.default_limit))
        
        # Validate
        if limit > self.max_limit:
            limit = self.max_limit
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0
        
        # Get items
        result = await db.execute(query.offset(offset).limit(limit))
        items = result.scalars().all()
        
        # Build response
        return {
            'items': items,
            'total': total,
            'offset': offset,
            'limit': limit,
            'has_more': offset + limit < total
        }