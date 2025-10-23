"""
Advanced Query Builder for FastAPI ORM

Provides powerful query construction utilities:
- Common Table Expressions (CTEs)
- Subquery builders
- Window functions
- CASE/WHEN statements
- Union/Intersect/Except operations

Example:
    ```python
    from fastapi_orm import QueryBuilder, WindowFunction
    
    # CTE Example
    qb = QueryBuilder(User)
    active_users_cte = qb.cte(
        qb.select().where(User.is_active == True),
        name="active_users"
    )
    results = await qb.select_from_cte(active_users_cte).execute(session)
    
    # Window Function Example
    ranked_users = await WindowFunction.rank_over(
        session,
        User,
        partition_by=[User.department],
        order_by=[User.salary.desc()]
    )
    ```
"""

from typing import Any, List, Optional, Type, TypeVar, Union, Dict, Tuple
from sqlalchemy import select, Select, CTE, case, func, literal, and_, or_, not_
from sqlalchemy.sql import expression
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query
from sqlalchemy.sql.selectable import Subquery

T = TypeVar('T')


class QueryBuilder:
    """
    Advanced query builder with support for CTEs, subqueries, and complex operations.
    
    Example:
        ```python
        qb = QueryBuilder(User)
        
        # Build a CTE
        active_cte = qb.cte(
            select(User).where(User.is_active == True),
            name="active_users"
        )
        
        # Query from CTE
        results = await qb.select_from_cte(active_cte).all(session)
        ```
    """
    
    def __init__(self, model: Type[T]):
        """
        Initialize query builder for a model.
        
        Args:
            model: The model class to build queries for
        """
        self.model = model
        self._query = select(model)
        self._ctes: List[CTE] = []
        self._has_explicit_select = False  # Track if .select() was called
    
    def select(self, *columns) -> 'QueryBuilder':
        """
        Select specific columns.
        
        Args:
            *columns: Columns to select
        
        Returns:
            QueryBuilder instance for chaining
        """
        if columns:
            self._query = select(*columns)
            self._has_explicit_select = True  # Mark that explicit columns were selected
        else:
            self._query = select(self.model)
        return self
    
    def where(self, *conditions) -> 'QueryBuilder':
        """
        Add WHERE conditions.
        
        Args:
            *conditions: Filter conditions
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.where(*conditions)
        return self
    
    def order_by(self, *columns) -> 'QueryBuilder':
        """
        Add ORDER BY clause.
        
        Args:
            *columns: Columns to order by
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.order_by(*columns)
        return self
    
    def limit(self, limit: int) -> 'QueryBuilder':
        """
        Add LIMIT clause.
        
        Args:
            limit: Maximum number of results
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.limit(limit)
        return self
    
    def offset(self, offset: int) -> 'QueryBuilder':
        """
        Add OFFSET clause.
        
        Args:
            offset: Number of results to skip
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.offset(offset)
        return self
    
    def group_by(self, *columns) -> 'QueryBuilder':
        """
        Add GROUP BY clause.
        
        Args:
            *columns: Columns to group by
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.group_by(*columns)
        return self
    
    def having(self, *conditions) -> 'QueryBuilder':
        """
        Add HAVING clause (must be used with group_by).
        
        Args:
            *conditions: Filter conditions for grouped results
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.having(*conditions)
        return self
    
    def distinct(self, *columns) -> 'QueryBuilder':
        """
        Add DISTINCT clause.
        
        Args:
            *columns: Optional columns for DISTINCT ON (PostgreSQL)
        
        Returns:
            QueryBuilder instance for chaining
        """
        if columns:
            self._query = self._query.distinct(*columns)
        else:
            self._query = self._query.distinct()
        return self
    
    def cte(self, query: Select, name: str, recursive: bool = False) -> CTE:
        """
        Create a Common Table Expression (CTE).
        
        Args:
            query: The SELECT query for the CTE
            name: Name of the CTE
            recursive: Whether this is a recursive CTE
        
        Returns:
            CTE object
        
        Example:
            ```python
            qb = QueryBuilder(User)
            active_users = qb.cte(
                select(User).where(User.is_active == True),
                name="active_users"
            )
            ```
        """
        cte = query.cte(name=name, recursive=recursive)
        self._ctes.append(cte)
        return cte
    
    def with_cte(self, *ctes: CTE) -> 'QueryBuilder':
        """
        Add CTEs to the query.
        
        Args:
            *ctes: CTE objects to add
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._ctes.extend(ctes)
        return self
    
    def select_from_cte(self, cte: CTE) -> 'QueryBuilder':
        """
        Select from a CTE.
        
        Args:
            cte: The CTE to select from
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = select(cte)
        return self
    
    def subquery(self, alias: Optional[str] = None) -> Subquery:
        """
        Convert current query to a subquery.
        
        Args:
            alias: Optional alias for the subquery
        
        Returns:
            Subquery object
        """
        return self._query.subquery(alias)
    
    def union(self, *queries: Select) -> 'QueryBuilder':
        """
        Create a UNION of multiple queries.
        
        Args:
            *queries: Queries to union
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.union(*queries)
        return self
    
    def union_all(self, *queries: Select) -> 'QueryBuilder':
        """
        Create a UNION ALL of multiple queries.
        
        Args:
            *queries: Queries to union
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.union_all(*queries)
        return self
    
    def intersect(self, *queries: Select) -> 'QueryBuilder':
        """
        Create an INTERSECT of multiple queries.
        
        Args:
            *queries: Queries to intersect
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.intersect(*queries)
        return self
    
    def except_(self, *queries: Select) -> 'QueryBuilder':
        """
        Create an EXCEPT of multiple queries.
        
        Args:
            *queries: Queries to except
        
        Returns:
            QueryBuilder instance for chaining
        """
        self._query = self._query.except_(*queries)
        return self
    
    def build(self) -> Select:
        """
        Build and return the final query with all CTEs.
        
        Returns:
            Complete SELECT statement
        """
        if self._ctes:
            for cte in self._ctes:
                self._query = self._query.add_cte(cte)
        return self._query
    
    async def execute(self, session: AsyncSession) -> List[T]:
        """
        Execute the query and return results.
        
        Args:
            session: Database session
        
        Returns:
            List of results
        """
        query = self.build()
        result = await session.execute(query)
        
        # Check if we're selecting specific columns or full entities
        # If .select() was explicitly called with columns, return Row objects
        # Otherwise return model instances
        if self._has_explicit_select:
            # Explicit column selection, return Row objects
            return list(result.all())
        else:
            # Entity query (selecting the full model), return model instances
            return list(result.scalars().all())
    
    async def first(self, session: AsyncSession) -> Optional[T]:
        """
        Execute the query and return first result.
        
        Args:
            session: Database session
        
        Returns:
            First result or None
        """
        query = self.build()
        result = await session.execute(query)
        return result.scalar_one_or_none()
    
    async def all(self, session: AsyncSession) -> List[T]:
        """
        Execute the query and return all results (alias for execute).
        
        Args:
            session: Database session
        
        Returns:
            List of all results
        """
        return await self.execute(session)
    
    async def count(self, session: AsyncSession) -> int:
        """
        Count results.
        
        Args:
            session: Database session
        
        Returns:
            Number of results
        """
        query = select(func.count()).select_from(self.build().subquery())
        result = await session.execute(query)
        return result.scalar()


class CaseBuilder:
    """
    Builder for CASE/WHEN statements.
    
    Example:
        ```python
        # Simple case
        case_stmt = (CaseBuilder()
            .when(User.age < 18, "Minor")
            .when(User.age < 65, "Adult")
            .else_("Senior")
            .build())
        
        query = select(User.name, case_stmt.label("age_group"))
        
        # With column
        case_stmt = (CaseBuilder(User.status)
            .when("active", 1)
            .when("inactive", 0)
            .else_(-1)
            .build())
        ```
    """
    
    def __init__(self, column: Optional[Any] = None):
        """
        Initialize CASE builder.
        
        Args:
            column: Optional column for simple CASE statements
        """
        self._column = column
        self._whens: List[Tuple[Any, Any]] = []
        self._else_value: Optional[Any] = None
    
    def when(self, condition: Any, value: Any) -> 'CaseBuilder':
        """
        Add a WHEN clause.
        
        Args:
            condition: Condition to check (or value if using column-based CASE)
            value: Value to return when condition is true
        
        Returns:
            CaseBuilder instance for chaining
        """
        self._whens.append((condition, value))
        return self
    
    def else_(self, value: Any) -> 'CaseBuilder':
        """
        Add ELSE clause.
        
        Args:
            value: Default value
        
        Returns:
            CaseBuilder instance for chaining
        """
        self._else_value = value
        return self
    
    def build(self):
        """
        Build the CASE statement.
        
        Returns:
            SQLAlchemy CASE expression
        """
        if self._column is not None:
            # Simple CASE: CASE column WHEN value1 THEN result1 ...
            whens = {cond: val for cond, val in self._whens}
            return case(whens, value=self._column, else_=self._else_value)
        else:
            # Searched CASE: CASE WHEN condition1 THEN result1 ...
            whens = self._whens
            return case(*whens, else_=self._else_value)


class WindowFunction:
    """
    Utilities for window functions (ROW_NUMBER, RANK, DENSE_RANK, etc.).
    
    Example:
        ```python
        # Rank users by salary within each department
        ranked = await WindowFunction.rank_over(
            session,
            User,
            partition_by=[User.department],
            order_by=[User.salary.desc()]
        )
        
        # Add row numbers
        numbered = await WindowFunction.row_number(
            session,
            User,
            order_by=[User.created_at]
        )
        ```
    """
    
    @staticmethod
    async def row_number(
        session: AsyncSession,
        model: Type[T],
        partition_by: Optional[List] = None,
        order_by: Optional[List] = None,
        filters: Optional[List] = None
    ) -> List[Tuple[T, int]]:
        """
        Add ROW_NUMBER() to query results.
        
        Args:
            session: Database session
            model: Model class
            partition_by: Columns to partition by
            order_by: Columns to order by
            filters: Optional WHERE conditions
        
        Returns:
            List of (model_instance, row_number) tuples
        """
        over_clause = {}
        if partition_by:
            over_clause['partition_by'] = partition_by
        if order_by:
            over_clause['order_by'] = order_by
        
        row_num = func.row_number().over(**over_clause).label('row_num')
        
        query = select(model, row_num)
        if filters:
            query = query.where(*filters)
        
        result = await session.execute(query)
        return [(row[0], row[1]) for row in result.all()]
    
    @staticmethod
    async def rank_over(
        session: AsyncSession,
        model: Type[T],
        partition_by: Optional[List] = None,
        order_by: Optional[List] = None,
        filters: Optional[List] = None,
        dense: bool = False
    ) -> List[Tuple[T, int]]:
        """
        Add RANK() or DENSE_RANK() to query results.
        
        Args:
            session: Database session
            model: Model class
            partition_by: Columns to partition by
            order_by: Columns to order by
            filters: Optional WHERE conditions
            dense: Use DENSE_RANK instead of RANK
        
        Returns:
            List of (model_instance, rank) tuples
        """
        over_clause = {}
        if partition_by:
            over_clause['partition_by'] = partition_by
        if order_by:
            over_clause['order_by'] = order_by
        
        rank_func = func.dense_rank() if dense else func.rank()
        rank_col = rank_func.over(**over_clause).label('rank')
        
        query = select(model, rank_col)
        if filters:
            query = query.where(*filters)
        
        result = await session.execute(query)
        return [(row[0], row[1]) for row in result.all()]
    
    @staticmethod
    async def ntile(
        session: AsyncSession,
        model: Type[T],
        n: int,
        partition_by: Optional[List] = None,
        order_by: Optional[List] = None,
        filters: Optional[List] = None
    ) -> List[Tuple[T, int]]:
        """
        Divide rows into N buckets using NTILE().
        
        Args:
            session: Database session
            model: Model class
            n: Number of buckets
            partition_by: Columns to partition by
            order_by: Columns to order by
            filters: Optional WHERE conditions
        
        Returns:
            List of (model_instance, bucket_number) tuples
        """
        over_clause = {}
        if partition_by:
            over_clause['partition_by'] = partition_by
        if order_by:
            over_clause['order_by'] = order_by
        
        ntile_col = func.ntile(n).over(**over_clause).label('bucket')
        
        query = select(model, ntile_col)
        if filters:
            query = query.where(*filters)
        
        result = await session.execute(query)
        return [(row[0], row[1]) for row in result.all()]
    
    @staticmethod
    def lag(column, offset: int = 1, default=None):
        """
        Get value from previous row.
        
        Args:
            column: Column to get value from
            offset: Number of rows back
            default: Default value if no previous row
        
        Returns:
            LAG window function
        """
        return func.lag(column, offset, default)
    
    @staticmethod
    def lead(column, offset: int = 1, default=None):
        """
        Get value from next row.
        
        Args:
            column: Column to get value from
            offset: Number of rows forward
            default: Default value if no next row
        
        Returns:
            LEAD window function
        """
        return func.lead(column, offset, default)
    
    @staticmethod
    def first_value(column):
        """
        Get first value in window.
        
        Args:
            column: Column to get value from
        
        Returns:
            FIRST_VALUE window function
        """
        return func.first_value(column)
    
    @staticmethod
    def last_value(column):
        """
        Get last value in window.
        
        Args:
            column: Column to get value from
        
        Returns:
            LAST_VALUE window function
        """
        return func.last_value(column)


class SubqueryBuilder:
    """
    Helper for building subqueries.
    
    Example:
        ```python
        # Find users with more than 5 posts
        post_count_subq = SubqueryBuilder.scalar_subquery(
            select(func.count(Post.id))
            .where(Post.author_id == User.id)
        )
        
        query = select(User).where(post_count_subq > 5)
        
        # Correlated subquery
        avg_price_subq = SubqueryBuilder.correlated(
            select(func.avg(Product.price))
            .where(Product.category_id == Category.id)
        )
        ```
    """
    
    @staticmethod
    def scalar_subquery(query: Select):
        """
        Create a scalar subquery (returns single value).
        
        Args:
            query: SELECT query
        
        Returns:
            Scalar subquery
        """
        return query.scalar_subquery()
    
    @staticmethod
    def exists(query: Select):
        """
        Create an EXISTS subquery.
        
        Args:
            query: SELECT query
        
        Returns:
            EXISTS expression
        """
        return query.exists()
    
    @staticmethod
    def in_subquery(column, query: Select):
        """
        Create an IN subquery.
        
        Args:
            column: Column to check
            query: SELECT query
        
        Returns:
            IN expression
        """
        return column.in_(query.scalar_subquery())
    
    @staticmethod
    def not_in_subquery(column, query: Select):
        """
        Create a NOT IN subquery.
        
        Args:
            column: Column to check
            query: SELECT query
        
        Returns:
            NOT IN expression
        """
        return column.not_in(query.scalar_subquery())
    
    @staticmethod
    def correlated(query: Select):
        """
        Create a correlated subquery.
        
        Args:
            query: SELECT query that references outer query
        
        Returns:
            Correlated subquery
        """
        return query.correlate()


# Convenience functions
def build_case(*whens, else_=None, column=None):
    """
    Quick helper to build CASE statements.
    
    Args:
        *whens: Tuples of (condition, value)
        else_: Default value
        column: Optional column for simple CASE
    
    Returns:
        CASE expression
    
    Example:
        ```python
        case_expr = build_case(
            (User.age < 18, "Minor"),
            (User.age < 65, "Adult"),
            else_="Senior"
        )
        ```
    """
    builder = CaseBuilder(column)
    for condition, value in whens:
        builder.when(condition, value)
    if else_ is not None:
        builder.else_(else_)
    return builder.build()


def cte(query: Select, name: str, recursive: bool = False) -> CTE:
    """
    Quick helper to create a CTE.
    
    Args:
        query: SELECT query
        name: CTE name
        recursive: Whether this is a recursive CTE
    
    Returns:
        CTE object
    """
    return query.cte(name=name, recursive=recursive)
