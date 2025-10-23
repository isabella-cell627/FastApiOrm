# FastAPI ORM v0.10.0 - Major Enhancement Release

## 🎉 Overview

Version 0.10.0 introduces powerful new features focused on **query building**, **performance optimization**, **constraint management**, and **operational excellence**. This release significantly enhances the library's capabilities for building production-grade applications.

---

## 🚀 New Features

### 1. Advanced Query Builder

**Comprehensive query construction toolkit with support for:**

#### Common Table Expressions (CTEs)
```python
from fastapi_orm import QueryBuilder, cte

# Create a CTE for high earners
qb = QueryBuilder(Employee)
high_earners_cte = cte(
    select(Employee).where(Employee.salary > 75000),
    name="high_earners"
)

# Query from the CTE
results = await qb.with_cte(high_earners_cte).execute(session)
```

#### Window Functions
```python
from fastapi_orm import WindowFunction

# Rank employees by salary within each department
ranked = await WindowFunction.rank_over(
    session,
    Employee,
    partition_by=[Employee.department_id],
    order_by=[Employee.salary.desc()],
    dense=True
)

# Add row numbers
numbered = await WindowFunction.row_number(
    session,
    Employee,
    order_by=[Employee.hire_date]
)

# Divide into quartiles
quartiles = await WindowFunction.ntile(
    session,
    Employee,
    n=4,
    order_by=[Employee.salary]
)
```

#### CASE/WHEN Statements
```python
from fastapi_orm import CaseBuilder, build_case

# Create salary bands
salary_band = build_case(
    (Employee.salary < 50000, "Entry Level"),
    (Employee.salary < 75000, "Mid Level"),
    (Employee.salary < 100000, "Senior Level"),
    else_="Executive"
)

query = select(Employee.name, Employee.salary, salary_band.label("band"))
```

#### Subquery Helpers
```python
from fastapi_orm import SubqueryBuilder

# Find users with more than 5 posts
post_count_subq = SubqueryBuilder.scalar_subquery(
    select(func.count(Post.id)).where(Post.author_id == User.id)
)

query = select(User).where(post_count_subq > 5)

# EXISTS subquery
high_earner_exists = SubqueryBuilder.exists(
    select(Employee.id)
    .where(Employee.department_id == Department.id)
    .where(Employee.salary > 80000)
)
```

#### Union/Intersect/Except Operations
```python
# UNION queries
high_earners = select(Employee).where(Employee.salary > 90000)
low_earners = select(Employee).where(Employee.salary < 40000)

qb = QueryBuilder(Employee)
qb._query = high_earners.union(low_earners)
results = await qb.execute(session)
```

---

### 2. Advanced Constraints & Validation

**Comprehensive constraint management system:**

#### CHECK Constraints
```python
from fastapi_orm import CheckConstraintValidator

# Create validator
validator = CheckConstraintValidator()
validator.add_range("price", min_value=0, max_value=10000)
validator.add_range("stock", min_value=0)
validator.add_regex("sku", r'^[A-Z]{3}-\d{4}$', "SKU must be format: ABC-1234")

# Validate data
await validator.validate({"sku": "ABC-1234", "price": 99.99, "stock": 100})
```

#### Unique Together Validation
```python
from fastapi_orm import UniqueTogetherValidator

class Product(Model):
    __tablename__ = "products"
    sku: str = StringField(max_length=50)
    company_id: int = IntegerField()
    
    __unique_together__ = [
        ("sku", "company_id"),  # SKU must be unique per company
    ]

# Automatic validation
await UniqueTogetherValidator.validate(session, Product, data)
```

#### Foreign Key Helpers
```python
from fastapi_orm import ForeignKeyHelper

# Validate foreign key exists
await ForeignKeyHelper.validate_fk(session, Company, "id", company_id)

# Check dependencies before delete
can_delete, reasons = await ForeignKeyHelper.can_delete(
    session,
    Company,
    company_id,
    [(Product, "company_id")]
)
```

#### Constraint Builder
```python
from fastapi_orm import ConstraintBuilder, create_constraint_set

builder = create_constraint_set(Product)
builder.add_check("positive_price", "price > 0")
builder.add_check("valid_stock", "stock >= 0")
builder.add_unique(["sku", "company_id"], name="unique_sku_per_company")
```

---

### 3. Enhanced Connection Pool Management

**Comprehensive pool monitoring and optimization:**

#### Pool Monitoring
```python
from fastapi_orm import PoolMonitor, create_pool_monitor

# Create monitor
monitor = PoolMonitor(db.engine, enable_tracking=True)

# Get pool statistics
stats = await monitor.get_stats()
print(f"Active connections: {stats['active_connections']}")
print(f"Idle connections: {stats['idle_connections']}")
print(f"Pool utilization: {stats['checked_out']}/{stats['pool_size']}")

# Check pool health
health = await monitor.check_health()
if not health['healthy']:
    print(f"Issues: {health['issues']}")
```

#### Connection Leak Detection
```python
from fastapi_orm import ConnectionLeakDetector

# Detect leaked connections
leaks = await monitor.detect_leaks(threshold_seconds=300)
for leak in leaks:
    print(f"Leaked connection: {leak.connection_id}, age: {leak.age_seconds}s")

# Continuous monitoring
detector = ConnectionLeakDetector(monitor)
await detector.start_monitoring()
```

#### Pool Optimization
```python
from fastapi_orm import PoolOptimizer

optimizer = PoolOptimizer(monitor)

# Get recommendations
recommendations = await optimizer.get_recommendations()
for rec in recommendations:
    print(f"- {rec}")

# Analyze usage patterns
analysis = await optimizer.analyze_patterns(duration_seconds=60)
print(f"Average utilization: {analysis['utilization_percentage']:.1f}%")
```

---

### 4. Performance Enhancements

**Automated performance analysis and optimization:**

#### N+1 Query Detection
```python
from fastapi_orm import N1Detector, create_n1_detector

# Create detector
detector = N1Detector(threshold=3, time_window=1.0)
detector.start()

# Your code that might have N+1
users = await User.all(session)
for user in users:
    posts = await Post.filter(session, user_id=user.id)  # N+1 detected!

# Get warnings
warnings = detector.get_warnings()
for warning in warnings:
    print(f"N+1: {warning.count} similar queries in {warning.total_time:.2f}s")
    print(f"Severity: {warning.severity}")

# Get comprehensive report
report = detector.get_report()
```

#### Query Analysis
```python
from fastapi_orm import QueryAnalyzer

analyzer = QueryAnalyzer(session)

# Analyze a query
analysis = await analyzer.analyze(
    select(User).where(User.age > 18).order_by(User.created_at)
)

print(f"Query: {analysis['sql']}")
print(f"Plan: {analysis['plan']}")
for suggestion in analysis['suggestions']:
    print(f"- {suggestion}")
```

#### Index Recommendations
```python
from fastapi_orm import IndexRecommender

recommender = IndexRecommender(min_frequency=3)

# Record query patterns
recommender.record_query("users", ["age", "is_active"])
recommender.record_query("users", ["email"])
recommender.record_query("users", ["age", "is_active"])  # Repeated

# Get recommendations
recommendations = recommender.get_recommendations()
for rec in recommendations:
    print(f"Create index: {rec['sql']}")
    print(f"  Frequency: {rec['frequency']}")
    print(f"  Benefit: {rec['estimated_benefit']}")
```

#### Performance Profiling
```python
from fastapi_orm import PerformanceProfiler

profiler = PerformanceProfiler()

# Profile operations
async with profiler.profile("user_queries"):
    users = await User.all(session)

async with profiler.profile("post_queries"):
    posts = await Post.all(session)

# Get statistics
stats = profiler.get_stats()
for operation, data in stats.items():
    print(f"{operation}: avg={data['avg_time']:.3f}s, count={data['count']}")

# Get slowest operations
slowest = profiler.get_slowest_operations(limit=10)
```

---

### 5. Database Views & Materialized Views

**Full support for views and materialized views:**

#### Regular Views
```python
from fastapi_orm import ViewManager, create_view_manager

view_mgr = ViewManager(engine)

# Create view
await view_mgr.create_view(
    "active_users",
    "SELECT * FROM users WHERE is_active = true",
    or_replace=True
)

# Drop view
await view_mgr.drop_view("active_users")

# List all views
views = await view_mgr.list_views()
```

#### Materialized Views (PostgreSQL)
```python
# Create materialized view
await view_mgr.create_materialized_view(
    "user_stats",
    '''
    SELECT department_id, 
           COUNT(*) as user_count,
           AVG(salary) as avg_salary
    FROM users
    GROUP BY department_id
    ''',
    with_data=True,
    indexes=["CREATE INDEX idx_user_stats_dept ON user_stats (department_id)"]
)

# Refresh materialized view
await view_mgr.refresh_materialized_view("user_stats")

# Concurrent refresh (requires unique index)
await view_mgr.refresh_materialized_view("user_stats", concurrently=True)

# List materialized views
mat_views = await view_mgr.list_materialized_views()
```

#### Automated Refresh
```python
from fastapi_orm import MaterializedViewRefresher

refresher = MaterializedViewRefresher(view_mgr)

# Schedule automatic refresh every hour
refresher.schedule("user_stats", interval_seconds=3600)

# Start background refresh
await refresher.start()
```

---

## 📈 Performance Improvements

- **Query Building**: Efficient CTE and subquery support
- **N+1 Detection**: Automatic detection prevents performance issues
- **Index Recommendations**: Data-driven index suggestions
- **Pool Monitoring**: Real-time connection tracking reduces leaks
- **Materialized Views**: Pre-computed results for complex queries

---

## 🔧 Technical Details

### New Modules

1. **`fastapi_orm/query_builder.py`**
   - `QueryBuilder`: Advanced query construction
   - `CaseBuilder`: CASE/WHEN statements
   - `WindowFunction`: Window function utilities
   - `SubqueryBuilder`: Subquery helpers

2. **`fastapi_orm/advanced_constraints.py`**
   - `ConstraintBuilder`: Database constraint management
   - `CheckConstraintValidator`: Application-level CHECK constraints
   - `UniqueTogetherValidator`: Multi-column uniqueness
   - `ForeignKeyHelper`: FK validation and dependency checking

3. **`fastapi_orm/pool_management.py`**
   - `PoolMonitor`: Connection pool monitoring
   - `PoolOptimizer`: Pool size recommendations
   - `ConnectionLeakDetector`: Leak detection and reporting

4. **`fastapi_orm/performance.py`**
   - `N1Detector`: N+1 query detection
   - `QueryAnalyzer`: Query plan analysis
   - `IndexRecommender`: Index recommendations
   - `PerformanceProfiler`: Operation profiling

5. **`fastapi_orm/views.py`**
   - `ViewManager`: View and materialized view management
   - `MaterializedViewRefresher`: Automated refresh scheduler

---

## 📚 Examples

New example files demonstrating all features:

- `examples/query_builder_example.py` - Advanced query building
- `examples/advanced_constraints_example.py` - Constraint management

---

## 🔄 Upgrade Guide

### Installation

No new dependencies required. All features use existing SQLAlchemy capabilities.

### Migration

No breaking changes. All new features are additive.

```python
# Import new features
from fastapi_orm import (
    QueryBuilder, WindowFunction, CaseBuilder,
    PoolMonitor, N1Detector, IndexRecommender,
    ViewManager, ConstraintBuilder
)

# All existing code continues to work unchanged
```

---

## 🐛 Bug Fixes

- Improved error handling in query builder
- Better connection pool cleanup
- Enhanced validation error messages

---

## 🙏 Acknowledgments

This release adds critical features for production deployments, making FastAPI ORM even more powerful for building scalable applications.

---

## 📝 Full Changelog

**Added:**
- Advanced query builder with CTEs, window functions, and subqueries
- Comprehensive constraint management system
- Connection pool monitoring and optimization
- N+1 query detection and prevention
- Query analysis and index recommendations
- Database views and materialized views support
- Performance profiling tools

**Changed:**
- Version bumped to 0.10.0

**Deprecated:**
- None

**Removed:**
- None

**Fixed:**
- Various edge cases in query handling

---

For more information, see the updated documentation and examples in the repository.
