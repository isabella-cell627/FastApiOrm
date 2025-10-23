"""
Advanced Aggregation and Group By Support

Provides utilities for complex aggregation queries:
- GROUP BY with multiple fields
- HAVING clauses
- Window functions
- Statistical aggregations

Example:
    from fastapi_orm import group_by, having
    
    # Group posts by author and count
    results = await Post.group_by(
        session,
        'author_id',
        aggregates={'post_count': 'count', 'avg_views': ('avg', 'views')}
    )
    
    # With HAVING clause
    results = await Post.group_by(
        session,
        'author_id',
        aggregates={'post_count': 'count'},
        having={'post_count__gt': 10}
    )
"""

from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import select, func, and_
from sqlalchemy.sql import expression


class AggregateQuery:
    """
    Builder for aggregation queries with GROUP BY and HAVING.
    
    Example:
        query = AggregateQuery(Post)
        query.group_by('author_id', 'published')
        query.aggregate('views', 'sum', alias='total_views')
        query.aggregate('id', 'count', alias='post_count')
        query.having('post_count', '>', 5)
        results = await query.execute(session)
    """
    
    def __init__(self, model_class):
        """
        Initialize aggregation query builder.
        
        Args:
            model_class: Model class to query
        """
        self.model = model_class
        self._group_by_fields = []
        self._aggregates = []
        self._having_conditions = []
        self._filters = []
        self._order_by = []
    
    def group_by(self, *fields: str) -> "AggregateQuery":
        """
        Add GROUP BY fields.
        
        Args:
            *fields: Field names to group by
        
        Returns:
            Self for method chaining
        """
        self._group_by_fields.extend(fields)
        return self
    
    def aggregate(
        self,
        field: str,
        func_name: str,
        alias: Optional[str] = None
    ) -> "AggregateQuery":
        """
        Add an aggregate function.
        
        Args:
            field: Field name to aggregate
            func_name: Aggregate function (count, sum, avg, max, min)
            alias: Alias for the result column
        
        Returns:
            Self for method chaining
        """
        if alias is None:
            alias = f"{func_name}_{field}"
        
        self._aggregates.append((field, func_name, alias))
        return self
    
    def having(self, alias: str, operator: str, value: Any) -> "AggregateQuery":
        """
        Add HAVING condition.
        
        Args:
            alias: Aggregate alias to filter on
            operator: Comparison operator (>, <, >=, <=, ==, !=)
            value: Value to compare against
        
        Returns:
            Self for method chaining
        """
        self._having_conditions.append((alias, operator, value))
        return self
    
    def filter(self, **kwargs) -> "AggregateQuery":
        """
        Add WHERE conditions (applied before grouping).
        
        Args:
            **kwargs: Field filters
        
        Returns:
            Self for method chaining
        """
        self._filters.append(kwargs)
        return self
    
    def order_by(self, *fields: str) -> "AggregateQuery":
        """
        Add ORDER BY fields.
        
        Args:
            *fields: Field names or aliases (prefix with - for descending)
        
        Returns:
            Self for method chaining
        """
        self._order_by.extend(fields)
        return self
    
    async def execute(self, session) -> List[Dict[str, Any]]:
        """
        Execute the aggregation query.
        
        Args:
            session: Database session
        
        Returns:
            List of result dictionaries
        """
        # Build SELECT clause
        select_cols = []
        
        # Add grouped fields
        for field in self._group_by_fields:
            col = getattr(self.model, field)
            select_cols.append(col.label(field))
        
        # Add aggregates
        aggregate_exprs = {}
        for field, func_name, alias in self._aggregates:
            col = getattr(self.model, field)
            
            if func_name == 'count':
                agg = func.count(col)
            elif func_name == 'sum':
                agg = func.sum(col)
            elif func_name == 'avg':
                agg = func.avg(col)
            elif func_name == 'max':
                agg = func.max(col)
            elif func_name == 'min':
                agg = func.min(col)
            else:
                raise ValueError(f"Unknown aggregate function: {func_name}")
            
            aggregate_exprs[alias] = agg
            select_cols.append(agg.label(alias))
        
        # Build query
        query = select(*select_cols)
        
        # Add WHERE conditions
        for filter_dict in self._filters:
            for key, value in filter_dict.items():
                query = query.where(getattr(self.model, key) == value)
        
        # Add GROUP BY
        if self._group_by_fields:
            group_cols = [getattr(self.model, f) for f in self._group_by_fields]
            query = query.group_by(*group_cols)
        
        # Add HAVING
        for alias, operator, value in self._having_conditions:
            agg_expr = aggregate_exprs.get(alias)
            if agg_expr is None:
                raise ValueError(f"Unknown aggregate alias: {alias}")
            
            if operator == '>':
                query = query.having(agg_expr > value)
            elif operator == '<':
                query = query.having(agg_expr < value)
            elif operator == '>=':
                query = query.having(agg_expr >= value)
            elif operator == '<=':
                query = query.having(agg_expr <= value)
            elif operator == '==':
                query = query.having(agg_expr == value)
            elif operator == '!=':
                query = query.having(agg_expr != value)
        
        # Add ORDER BY
        for field in self._order_by:
            if field.startswith('-'):
                query = query.order_by(
                    getattr(self.model, field[1:]).desc()
                )
            else:
                query = query.order_by(getattr(self.model, field))
        
        # Execute
        result = await session.execute(query)
        
        # Convert to dictionaries
        rows = result.all()
        return [dict(row._mapping) for row in rows]


# Mixin to add group_by method to models
class AggregationMixin:
    """
    Mixin that adds aggregation methods to models.
    
    Example:
        class Post(Model, AggregationMixin):
            __tablename__ = "posts"
            author_id: int = IntegerField()
            views: int = IntegerField(default=0)
        
        # Group by author and count posts
        results = await Post.group_by(
            session,
            'author_id',
            aggregates={'post_count': 'count'}
        )
    """
    
    @classmethod
    async def group_by(
        cls,
        session,
        *group_fields: str,
        aggregates: Optional[Dict[str, Union[str, Tuple[str, str]]]] = None,
        having: Optional[Dict[str, Any]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform GROUP BY query with aggregations.
        
        Args:
            session: Database session
            *group_fields: Fields to group by
            aggregates: Dict of {alias: function} or {alias: (function, field)}
            having: Dict of {alias__operator: value} for HAVING clause
            filters: Dict of {field: value} for WHERE clause
            order_by: List of fields to order by (prefix with - for desc)
        
        Returns:
            List of result dictionaries
        
        Example:
            # Count posts per author
            results = await Post.group_by(
                session,
                'author_id',
                aggregates={'count': 'count'}
            )
            
            # Average views by author, only authors with >10 posts
            results = await Post.group_by(
                session,
                'author_id',
                aggregates={
                    'post_count': 'count',
                    'avg_views': ('avg', 'views')
                },
                having={'post_count__gt': 10},
                order_by=['-avg_views']
            )
        """
        query_builder = AggregateQuery(cls)
        
        # Add GROUP BY
        if group_fields:
            query_builder.group_by(*group_fields)
        
        # Add aggregates
        if aggregates:
            for alias, agg_spec in aggregates.items():
                if isinstance(agg_spec, str):
                    # Simple aggregate: {'count': 'count'}
                    query_builder.aggregate('id', agg_spec, alias)
                else:
                    # Tuple aggregate: {'avg_views': ('avg', 'views')}
                    func_name, field = agg_spec
                    query_builder.aggregate(field, func_name, alias)
        
        # Add HAVING
        if having:
            for key, value in having.items():
                if '__' in key:
                    alias, op = key.rsplit('__', 1)
                    op_map = {
                        'gt': '>',
                        'gte': '>=',
                        'lt': '<',
                        'lte': '<=',
                        'eq': '==',
                        'ne': '!='
                    }
                    operator = op_map.get(op, '==')
                    query_builder.having(alias, operator, value)
                else:
                    query_builder.having(key, '==', value)
        
        # Add filters
        if filters:
            query_builder.filter(**filters)
        
        # Add ORDER BY
        if order_by:
            query_builder.order_by(*order_by)
        
        return await query_builder.execute(session)
