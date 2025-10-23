import csv
import json
import logging
from typing import AsyncIterator, Any, Dict, List, Optional, Callable
from io import StringIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi.responses import StreamingResponse


class QueryStreamer:
    """
    Stream large query results efficiently without loading all data into memory.
    
    Supports:
    - Async iteration over query results
    - Batch processing
    - Format conversion (JSON, CSV, JSONL)
    - Memory-efficient pagination
    - Progress tracking
    
    Example:
        ```python
        from fastapi_orm import QueryStreamer, User
        
        streamer = QueryStreamer(User, batch_size=100)
        
        # Stream as async iterator
        async for batch in streamer.stream_batches(session):
            for user in batch:
                await process_user(user)
        
        # Stream as JSON
        response = await streamer.stream_json(session)
        return response  # FastAPI StreamingResponse
        ```
    """
    
    def __init__(
        self,
        model_class,
        batch_size: int = 100,
        order_by: Optional[str] = None
    ):
        """
        Initialize query streamer.
        
        Args:
            model_class: Model class to query
            batch_size: Number of records per batch
            order_by: Field to order by (default: primary key)
        """
        self.model_class = model_class
        self.batch_size = batch_size
        self.order_by = order_by or "id"
        self._logger = logging.getLogger("fastapi_orm.streaming")
    
    async def stream_records(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator:
        """
        Stream individual records one at a time.
        
        Args:
            session: Database session
            filters: Optional filter criteria
        
        Yields:
            Individual model instances
        """
        offset = 0
        
        while True:
            query = select(self.model_class.__table__)
            
            if filters:
                for key, value in filters.items():
                    column = getattr(self.model_class.__table__.c, key)
                    query = query.where(column == value)
            
            query = query.order_by(
                getattr(self.model_class.__table__.c, self.order_by)
            ).offset(offset).limit(self.batch_size)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            if not rows:
                break
            
            for row in rows:
                yield dict(row._mapping)
            
            offset += self.batch_size
            
            if len(rows) < self.batch_size:
                break
    
    async def stream_batches(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[List]:
        """
        Stream records in batches.
        
        Args:
            session: Database session
            filters: Optional filter criteria
        
        Yields:
            Lists of model instances (batches)
        """
        offset = 0
        
        while True:
            query = select(self.model_class.__table__)
            
            if filters:
                for key, value in filters.items():
                    column = getattr(self.model_class.__table__.c, key)
                    query = query.where(column == value)
            
            query = query.order_by(
                getattr(self.model_class.__table__.c, self.order_by)
            ).offset(offset).limit(self.batch_size)
            
            result = await session.execute(query)
            rows = result.fetchall()
            
            if not rows:
                break
            
            batch = [dict(row._mapping) for row in rows]
            yield batch
            
            offset += self.batch_size
            
            if len(rows) < self.batch_size:
                break
    
    async def stream_json(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        include_metadata: bool = True
    ) -> StreamingResponse:
        """
        Stream results as newline-delimited JSON (JSONL).
        
        Args:
            session: Database session
            filters: Optional filter criteria
            include_metadata: Include metadata in response
        
        Returns:
            FastAPI StreamingResponse
        """
        async def generate():
            count = 0
            
            if include_metadata:
                total = await self.count_total(session, filters)
                metadata = {
                    "total": total,
                    "batch_size": self.batch_size,
                    "format": "jsonl"
                }
                yield json.dumps({"metadata": metadata}) + "\n"
            
            async for record in self.stream_records(session, filters):
                yield json.dumps(record) + "\n"
                count += 1
            
            if include_metadata:
                footer = {"summary": {"records_streamed": count}}
                yield json.dumps(footer) + "\n"
        
        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={
                "Content-Disposition": f"attachment; filename={self.model_class.__tablename__}.jsonl"
            }
        )
    
    async def stream_csv(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None,
        include_headers: bool = True
    ) -> StreamingResponse:
        """
        Stream results as CSV.
        
        Args:
            session: Database session
            filters: Optional filter criteria
            include_headers: Include CSV headers
        
        Returns:
            FastAPI StreamingResponse
        """
        async def generate():
            first_record = True
            headers = None
            
            async for record in self.stream_records(session, filters):
                if first_record and include_headers:
                    headers = record.keys()
                    output = StringIO()
                    writer = csv.DictWriter(output, fieldnames=headers)
                    writer.writeheader()
                    yield output.getvalue()
                    first_record = False
                
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=headers or record.keys())
                writer.writerow(record)
                yield output.getvalue()
        
        return StreamingResponse(
            generate(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={self.model_class.__tablename__}.csv"
            }
        )
    
    async def count_total(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count total records matching filters.
        
        Args:
            session: Database session
            filters: Optional filter criteria
        
        Returns:
            Total count
        """
        query = select(func.count()).select_from(self.model_class.__table__)
        
        if filters:
            for key, value in filters.items():
                column = getattr(self.model_class.__table__.c, key)
                query = query.where(column == value)
        
        result = await session.execute(query)
        return result.scalar_one()


class CursorPaginator:
    """
    Cursor-based pagination for efficient traversal of large datasets.
    
    More efficient than offset-based pagination for large tables.
    Prevents issues with changing data during pagination.
    
    Example:
        ```python
        from fastapi_orm import CursorPaginator, User
        
        paginator = CursorPaginator(User, page_size=50)
        
        # First page
        result = await paginator.get_page(session, cursor=None)
        users = result["data"]
        next_cursor = result["next_cursor"]
        
        # Next page
        result = await paginator.get_page(session, cursor=next_cursor)
        ```
    """
    
    def __init__(
        self,
        model_class,
        page_size: int = 50,
        cursor_field: str = "id",
        order: str = "asc"
    ):
        """
        Initialize cursor paginator.
        
        Args:
            model_class: Model class to paginate
            page_size: Records per page
            cursor_field: Field to use for cursor (should be indexed)
            order: Sort order ("asc" or "desc")
        """
        self.model_class = model_class
        self.page_size = page_size
        self.cursor_field = cursor_field
        self.order = order.lower()
        self._logger = logging.getLogger("fastapi_orm.streaming.cursor")
    
    async def get_page(
        self,
        session: AsyncSession,
        cursor: Optional[Any] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Get a page of results using cursor.
        
        Args:
            session: Database session
            cursor: Cursor value from previous page (None for first page)
            filters: Optional filter criteria
        
        Returns:
            Dictionary with data, next_cursor, has_more, total
        """
        query = select(self.model_class.__table__)
        
        if filters:
            for key, value in filters.items():
                column = getattr(self.model_class.__table__.c, key)
                query = query.where(column == value)
        
        cursor_column = getattr(self.model_class.__table__.c, self.cursor_field)
        
        if cursor is not None:
            if self.order == "asc":
                query = query.where(cursor_column > cursor)
            else:
                query = query.where(cursor_column < cursor)
        
        if self.order == "asc":
            query = query.order_by(cursor_column.asc())
        else:
            query = query.order_by(cursor_column.desc())
        
        query = query.limit(self.page_size + 1)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        has_more = len(rows) > self.page_size
        data = [dict(row._mapping) for row in rows[:self.page_size]]
        
        next_cursor = None
        if has_more and data:
            next_cursor = data[-1][self.cursor_field]
        
        total = await self._count_total(session, filters)
        
        return {
            "data": data,
            "next_cursor": next_cursor,
            "has_more": has_more,
            "page_size": self.page_size,
            "total": total
        }
    
    async def _count_total(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> int:
        """Count total matching records"""
        query = select(func.count()).select_from(self.model_class.__table__)
        
        if filters:
            for key, value in filters.items():
                column = getattr(self.model_class.__table__.c, key)
                query = query.where(column == value)
        
        result = await session.execute(query)
        return result.scalar_one()


async def stream_with_transform(
    streamer: QueryStreamer,
    session: AsyncSession,
    transform: Callable[[Dict], Dict],
    filters: Optional[Dict[str, Any]] = None
) -> AsyncIterator[Dict]:
    """
    Stream records with transformation function applied.
    
    Args:
        streamer: QueryStreamer instance
        session: Database session
        transform: Function to transform each record
        filters: Optional filter criteria
    
    Yields:
        Transformed records
    
    Example:
        ```python
        def anonymize_user(user):
            user["email"] = "***@***.com"
            return user
        
        async for user in stream_with_transform(streamer, session, anonymize_user):
            print(user)
        ```
    """
    async for record in streamer.stream_records(session, filters):
        yield transform(record)


async def stream_with_filter(
    streamer: QueryStreamer,
    session: AsyncSession,
    predicate: Callable[[Dict], bool],
    filters: Optional[Dict[str, Any]] = None
) -> AsyncIterator[Dict]:
    """
    Stream records with additional filtering logic.
    
    Args:
        streamer: QueryStreamer instance
        session: Database session
        predicate: Function that returns True for records to include
        filters: Optional filter criteria
    
    Yields:
        Filtered records
    
    Example:
        ```python
        async for user in stream_with_filter(
            streamer,
            session,
            lambda u: u["age"] > 18
        ):
            print(user)
        ```
    """
    async for record in streamer.stream_records(session, filters):
        if predicate(record):
            yield record


class BatchProcessor:
    """
    Process large datasets in batches with error handling and progress tracking.
    
    Example:
        ```python
        from fastapi_orm import BatchProcessor, User
        
        async def process_user(user):
            # Update user
            pass
        
        processor = BatchProcessor(
            model_class=User,
            batch_size=100,
            process_func=process_user
        )
        
        result = await processor.process_all(session)
        print(f"Processed {result['processed']} records")
        ```
    """
    
    def __init__(
        self,
        model_class,
        batch_size: int = 100,
        process_func: Optional[Callable] = None,
        on_error: str = "skip"
    ):
        """
        Initialize batch processor.
        
        Args:
            model_class: Model class to process
            batch_size: Records per batch
            process_func: Async function to process each record
            on_error: Error handling ("skip", "stop", "continue")
        """
        self.model_class = model_class
        self.batch_size = batch_size
        self.process_func = process_func
        self.on_error = on_error
        self._logger = logging.getLogger("fastapi_orm.streaming.batch")
    
    async def process_all(
        self,
        session: AsyncSession,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process all matching records.
        
        Args:
            session: Database session
            filters: Optional filter criteria
        
        Returns:
            Dictionary with processing results
        """
        streamer = QueryStreamer(self.model_class, batch_size=self.batch_size)
        
        total_processed = 0
        total_errors = 0
        error_details = []
        
        async for batch in streamer.stream_batches(session, filters):
            for record in batch:
                try:
                    if self.process_func:
                        await self.process_func(record)
                    total_processed += 1
                    
                except Exception as e:
                    total_errors += 1
                    error_details.append({
                        "record_id": record.get("id"),
                        "error": str(e)
                    })
                    
                    self._logger.error(f"Error processing record: {e}")
                    
                    if self.on_error == "stop":
                        raise
                    elif self.on_error == "skip":
                        continue
            
            await session.commit()
        
        return {
            "processed": total_processed,
            "errors": total_errors,
            "error_details": error_details,
            "success_rate": (total_processed / (total_processed + total_errors) * 100)
                if (total_processed + total_errors) > 0 else 0
        }
