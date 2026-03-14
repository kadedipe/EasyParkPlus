"""
Base CRUD class with common operations.
"""

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import select, update, delete

from ..db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Base class for CRUD operations.
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        Initialize CRUD with model class.
        
        Args:
            model: SQLAlchemy model class
        """
        self.model = model
    
    async def get(
        self,
        db: AsyncSession,
        id: str
    ) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Optional[ModelType]: Found record or None
        """
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        db: AsyncSession,
        *,
        skip: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> List[ModelType]:
        """
        Get multiple records with pagination.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            
        Returns:
            List[ModelType]: List of records
        """
        query = select(self.model)
        
        # Apply sorting
        if sort_by and hasattr(self.model, sort_by):
            sort_column = getattr(self.model, sort_by)
            if sort_order.lower() == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(self.model.created_at.desc())
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_count(
        self,
        db: AsyncSession,
        *,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Get total count of records with optional filters.
        
        Args:
            db: Database session
            filters: Optional filters to apply
            
        Returns:
            int: Total count
        """
        query = select(func.count()).select_from(self.model)
        
        # Apply filters if provided
        if filters:
            for key, value in filters.items():
                if hasattr(self.model, key) and value is not None:
                    query = query.where(getattr(self.model, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def create(
        self,
        db: AsyncSession,
        *,
        obj_in: CreateSchemaType
    ) -> ModelType:
        """
        Create new record.
        
        Args:
            db: Database session
            obj_in: Pydantic schema with creation data
            
        Returns:
            ModelType: Created record
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update record.
        
        Args:
            db: Database session
            db_obj: Existing database object
            obj_in: Pydantic schema or dict with update data
            
        Returns:
            ModelType: Updated record
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove(
        self,
        db: AsyncSession,
        *,
        id: str
    ) -> Optional[ModelType]:
        """
        Remove record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Optional[ModelType]: Removed record or None
        """
        db_obj = await self.get(db, id=id)
        if db_obj:
            await db.delete(db_obj)
            await db.commit()
        return db_obj
    
    async def get_multi_by_ids(
        self,
        db: AsyncSession,
        *,
        ids: List[str]
    ) -> List[ModelType]:
        """
        Get multiple records by IDs.
        
        Args:
            db: Database session
            ids: List of record IDs
            
        Returns:
            List[ModelType]: List of found records
        """
        query = select(self.model).where(self.model.id.in_(ids))
        result = await db.execute(query)
        return result.scalars().all()
    
    async def exists(
        self,
        db: AsyncSession,
        *,
        id: str
    ) -> bool:
        """
        Check if record exists by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            bool: True if exists, False otherwise
        """
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.first() is not None