"""
Performance Enhancements and Optimization Tools

Provides tools for identifying and fixing performance issues:
- N+1 query detection and warnings
- Query plan analysis
- Index recommendations
- Query optimization suggestions
- Slow query detection
- Performance profiling

Example:
    ```python
    from fastapi_orm import N1Detector, QueryAnalyzer, IndexRecommender
    
    # Detect N+1 queries
    detector = N1Detector()
    detector.start()
    
    # ... run queries ...
    
    warnings = detector.get_warnings()
    for warning in warnings:
        print(f"N+1 detected: {warning}")
    ```
"""

import re
import logging
import time
from typing import Dict, List, Optional, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.sql import Select


logger = logging.getLogger(__name__)


@dataclass
class QueryInfo:
    """Information about a single query."""
    sql: str
    timestamp: float
    duration: float = 0.0
    stack_trace: Optional[str] = None
    params: Optional[Dict] = None


@dataclass
class N1Warning:
    """Warning about potential N+1 query."""
    pattern: str
    count: int
    total_time: float
    queries: List[QueryInfo] = field(default_factory=list)
    severity: str = "medium"  # low, medium, high, critical


class N1Detector:
    """
    Detect N+1 query problems automatically.
    
    N+1 queries occur when you load a collection and then execute a query
    for each item in the collection (e.g., loading users then loading posts
    for each user separately).
    
    Example:
        ```python
        detector = N1Detector()
        detector.start()
        
        # Your code that might have N+1
        users = await User.all(session)
        for user in users:
            posts = await Post.filter(session, user_id=user.id)  # N+1!
        
        # Check for warnings
        warnings = detector.get_warnings()
        for warning in warnings:
            print(f"N+1 detected: {warning.count} similar queries in {warning.total_time:.2f}s")
        ```
    """
    
    def __init__(
        self,
        threshold: int = 3,
        time_window: float = 1.0,
        enabled: bool = True
    ):
        """
        Initialize N+1 detector.
        
        Args:
            threshold: Number of similar queries to trigger warning
            time_window: Time window in seconds to group queries
            enabled: Enable detection
        """
        self.threshold = threshold
        self.time_window = time_window
        self.enabled = enabled
        
        self._query_history: List[QueryInfo] = []
        self._warnings: List[N1Warning] = []
        self._is_running = False
    
    def start(self):
        """Start N+1 detection."""
        self.enabled = True
        self._is_running = True
    
    def stop(self):
        """Stop N+1 detection."""
        self._is_running = False
    
    def record_query(self, sql: str, duration: float = 0.0, params: Optional[Dict] = None):
        """
        Record a query for analysis.
        
        Args:
            sql: SQL query string
            duration: Query execution time
            params: Query parameters
        """
        if not self.enabled:
            return
        
        query_info = QueryInfo(
            sql=sql,
            timestamp=time.time(),
            duration=duration,
            params=params
        )
        
        self._query_history.append(query_info)
        
        # Analyze for N+1 patterns
        self._analyze_recent_queries()
    
    def _normalize_query(self, sql: str) -> str:
        """Normalize SQL query for pattern matching."""
        # Remove parameter values
        normalized = re.sub(r'\b\d+\b', '?', sql)
        # Remove string literals
        normalized = re.sub(r"'[^']*'", '?', normalized)
        # Remove whitespace variations
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip().lower()
    
    def _analyze_recent_queries(self):
        """Analyze recent queries for N+1 patterns."""
        if len(self._query_history) < self.threshold:
            return
        
        now = time.time()
        recent_queries = [
            q for q in self._query_history
            if now - q.timestamp <= self.time_window
        ]
        
        if len(recent_queries) < self.threshold:
            return
        
        # Group queries by normalized pattern
        patterns: Dict[str, List[QueryInfo]] = defaultdict(list)
        for query in recent_queries:
            pattern = self._normalize_query(query.sql)
            patterns[pattern].append(query)
        
        # Check for N+1 patterns
        for pattern, queries in patterns.items():
            if len(queries) >= self.threshold:
                # Check if we already have this warning
                existing = next(
                    (w for w in self._warnings if w.pattern == pattern),
                    None
                )
                
                total_time = sum(q.duration for q in queries)
                
                # Determine severity
                severity = "low"
                if len(queries) > 20:
                    severity = "critical"
                elif len(queries) > 10:
                    severity = "high"
                elif len(queries) > 5:
                    severity = "medium"
                
                if existing:
                    # Update existing warning
                    existing.count = len(queries)
                    existing.total_time = total_time
                    existing.severity = severity
                else:
                    # Create new warning
                    warning = N1Warning(
                        pattern=pattern,
                        count=len(queries),
                        total_time=total_time,
                        queries=queries[:10],  # Keep first 10 as examples
                        severity=severity
                    )
                    self._warnings.append(warning)
                    
                    logger.warning(
                        f"N+1 query detected: {len(queries)} similar queries "
                        f"in {self.time_window}s window"
                    )
    
    def get_warnings(self, severity: Optional[str] = None) -> List[N1Warning]:
        """
        Get N+1 warnings.
        
        Args:
            severity: Filter by severity (low, medium, high, critical)
        
        Returns:
            List of N+1 warnings
        """
        if severity:
            return [w for w in self._warnings if w.severity == severity]
        return self._warnings
    
    def clear_warnings(self):
        """Clear all warnings."""
        self._warnings.clear()
    
    def analyze(self):
        """Manually trigger analysis of recorded queries."""
        self._analyze_recent_queries()
    
    def clear(self):
        """Clear all query history and warnings."""
        self._query_history.clear()
        self._warnings.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get detector statistics.
        
        Returns:
            Dictionary with query statistics
        """
        total_time = sum(q.duration for q in self._query_history)
        return {
            "total_queries": len(self._query_history),
            "total_time": total_time,
            "total_warnings": len(self._warnings),
            "enabled": self.enabled,
            "is_running": self._is_running
        }
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get comprehensive N+1 detection report.
        
        Returns:
            Report dictionary
        """
        return {
            'total_warnings': len(self._warnings),
            'by_severity': {
                'critical': len([w for w in self._warnings if w.severity == 'critical']),
                'high': len([w for w in self._warnings if w.severity == 'high']),
                'medium': len([w for w in self._warnings if w.severity == 'medium']),
                'low': len([w for w in self._warnings if w.severity == 'low']),
            },
            'total_queries_analyzed': len(self._query_history),
            'warnings': [
                {
                    'pattern': w.pattern,
                    'count': w.count,
                    'total_time': w.total_time,
                    'severity': w.severity,
                }
                for w in sorted(self._warnings, key=lambda x: x.count, reverse=True)
            ]
        }


class QueryAnalyzer:
    """
    Analyze query plans and provide optimization suggestions.
    
    Example:
        ```python
        analyzer = QueryAnalyzer(session)
        
        # Analyze a query
        analysis = await analyzer.analyze(
            select(User).where(User.age > 18)
        )
        
        print(f"Estimated cost: {analysis['cost']}")
        for suggestion in analysis['suggestions']:
            print(f"- {suggestion}")
        ```
    """
    
    def __init__(self, session: AsyncSession):
        """
        Initialize query analyzer.
        
        Args:
            session: Database session
        """
        self.session = session
    
    async def analyze(self, query: Select) -> Dict[str, Any]:
        """
        Analyze a query and provide insights.
        
        Args:
            query: SQLAlchemy SELECT query
        
        Returns:
            Analysis results
        """
        # Compile query to SQL
        compiled = query.compile(compile_kwargs={"literal_binds": True})
        sql = str(compiled)
        
        # Get query plan
        plan = await self._get_query_plan(sql)
        
        # Analyze plan
        suggestions = self._analyze_plan(plan, sql)
        
        return {
            'sql': sql,
            'plan': plan,
            'suggestions': suggestions,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    async def _get_query_plan(self, sql: str) -> str:
        """Get database query execution plan."""
        try:
            # PostgreSQL
            result = await self.session.execute(text(f"EXPLAIN {sql}"))
            plan_lines = [row[0] for row in result.fetchall()]
            return "\n".join(plan_lines)
        except:
            try:
                # SQLite
                result = await self.session.execute(text(f"EXPLAIN QUERY PLAN {sql}"))
                plan_lines = [str(row) for row in result.fetchall()]
                return "\n".join(plan_lines)
            except:
                return "Query plan not available"
    
    def _analyze_plan(self, plan: str, sql: str) -> List[str]:
        """Analyze query plan and generate suggestions."""
        suggestions = []
        
        # Check for sequential scans
        if 'seq scan' in plan.lower() or 'scan' in plan.lower():
            suggestions.append(
                "Sequential scan detected - consider adding an index"
            )
        
        # Check for sort operations
        if 'sort' in plan.lower():
            suggestions.append(
                "Sort operation detected - consider adding index on ORDER BY columns"
            )
        
        # Check for temp tables
        if 'temp' in plan.lower():
            suggestions.append(
                "Temporary table used - query may benefit from optimization"
            )
        
        # Check for nested loops
        if 'nested loop' in plan.lower():
            suggestions.append(
                "Nested loop join detected - ensure proper indexes on join columns"
            )
        
        # Check for missing WHERE clause
        if 'where' not in sql.lower() and 'select *' in sql.lower():
            suggestions.append(
                "Full table scan detected - add WHERE clause to filter results"
            )
        
        # Check for SELECT *
        if 'select *' in sql.lower():
            suggestions.append(
                "SELECT * detected - specify only needed columns for better performance"
            )
        
        if not suggestions:
            suggestions.append("Query appears to be well-optimized")
        
        return suggestions


class IndexRecommender:
    """
    Recommend indexes based on query patterns.
    
    Example:
        ```python
        recommender = IndexRecommender()
        
        # Record queries
        recommender.record_query(User, ["age", "is_active"])
        recommender.record_query(User, ["email"])
        
        # Get recommendations
        recommendations = recommender.get_recommendations()
        for rec in recommendations:
            print(f"Create index on {rec['table']}.{rec['columns']}")
        ```
    """
    
    def __init__(self, min_frequency: int = 3):
        """
        Initialize index recommender.
        
        Args:
            min_frequency: Minimum query frequency to recommend index
        """
        self.min_frequency = min_frequency
        self._query_patterns: Dict[Tuple[str, tuple], int] = defaultdict(int)
        self._existing_indexes: Set[Tuple[str, tuple]] = set()
    
    def record_query(self, table_name: str, columns: List[str]):
        """
        Record a query pattern for analysis.
        
        Args:
            table_name: Table name
            columns: Columns used in WHERE/JOIN/ORDER BY
        """
        key = (table_name, tuple(sorted(columns)))
        self._query_patterns[key] += 1
    
    def add_existing_index(self, table_name: str, columns: List[str]):
        """
        Register an existing index.
        
        Args:
            table_name: Table name
            columns: Index columns
        """
        key = (table_name, tuple(sorted(columns)))
        self._existing_indexes.add(key)
    
    def get_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get index recommendations based on query patterns.
        
        Returns:
            List of index recommendations
        """
        recommendations = []
        
        for (table, columns), frequency in self._query_patterns.items():
            if frequency < self.min_frequency:
                continue
            
            # Check if index already exists
            if (table, columns) in self._existing_indexes:
                continue
            
            # Check for single-column vs composite index
            index_type = "composite" if len(columns) > 1 else "single-column"
            
            # Estimate benefit
            benefit = "high" if frequency > 10 else "medium" if frequency > 5 else "low"
            
            recommendations.append({
                'table': table,
                'columns': list(columns),
                'frequency': frequency,
                'type': index_type,
                'estimated_benefit': benefit,
                'sql': f"CREATE INDEX idx_{table}_{'_'.join(columns)} ON {table} ({', '.join(columns)})"
            })
        
        # Sort by frequency (most beneficial first)
        recommendations.sort(key=lambda x: x['frequency'], reverse=True)
        
        return recommendations
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get comprehensive index recommendation report.
        
        Returns:
            Report dictionary
        """
        recommendations = self.get_recommendations()
        
        return {
            'total_recommendations': len(recommendations),
            'high_priority': len([r for r in recommendations if r['estimated_benefit'] == 'high']),
            'medium_priority': len([r for r in recommendations if r['estimated_benefit'] == 'medium']),
            'low_priority': len([r for r in recommendations if r['estimated_benefit'] == 'low']),
            'recommendations': recommendations,
        }


class PerformanceProfiler:
    """
    Profile database operations and identify bottlenecks.
    
    Example:
        ```python
        profiler = PerformanceProfiler()
        
        async with profiler.profile("user_queries"):
            users = await User.all(session)
        
        stats = profiler.get_stats()
        ```
    """
    
    def __init__(self):
        """Initialize performance profiler."""
        self._operations: Dict[str, List[float]] = defaultdict(list)
        self._current_operation: Optional[str] = None
        self._start_time: Optional[float] = None
    
    async def profile(self, operation_name: str):
        """
        Context manager for profiling an operation.
        
        Args:
            operation_name: Name of the operation
        """
        class ProfileContext:
            def __init__(ctx_self, profiler, name):
                ctx_self.profiler = profiler
                ctx_self.name = name
            
            async def __aenter__(ctx_self):
                ctx_self.profiler._current_operation = ctx_self.name
                ctx_self.profiler._start_time = time.time()
                return ctx_self
            
            async def __aexit__(ctx_self, *args):
                duration = time.time() - ctx_self.profiler._start_time
                ctx_self.profiler._operations[ctx_self.name].append(duration)
                ctx_self.profiler._current_operation = None
                ctx_self.profiler._start_time = None
        
        return ProfileContext(self, operation_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get profiling statistics.
        
        Returns:
            Statistics dictionary
        """
        stats = {}
        
        for operation, durations in self._operations.items():
            stats[operation] = {
                'count': len(durations),
                'total_time': sum(durations),
                'avg_time': sum(durations) / len(durations),
                'min_time': min(durations),
                'max_time': max(durations),
            }
        
        return stats
    
    def get_slowest_operations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get slowest operations.
        
        Args:
            limit: Number of results to return
        
        Returns:
            List of slowest operations
        """
        stats = self.get_stats()
        
        operations = [
            {
                'operation': name,
                **data
            }
            for name, data in stats.items()
        ]
        
        # Sort by average time
        operations.sort(key=lambda x: x['avg_time'], reverse=True)
        
        return operations[:limit]


def create_n1_detector(**kwargs) -> N1Detector:
    """
    Create an N+1 query detector.
    
    Args:
        **kwargs: Arguments for N1Detector
    
    Returns:
        N1Detector instance
    """
    return N1Detector(**kwargs)


def create_query_analyzer(session: AsyncSession) -> QueryAnalyzer:
    """
    Create a query analyzer.
    
    Args:
        session: Database session
    
    Returns:
        QueryAnalyzer instance
    """
    return QueryAnalyzer(session)


def create_index_recommender(**kwargs) -> IndexRecommender:
    """
    Create an index recommender.
    
    Args:
        **kwargs: Arguments for IndexRecommender
    
    Returns:
        IndexRecommender instance
    """
    return IndexRecommender(**kwargs)
