# FastAPI ORM v0.5.0 - Major Feature Release

**Release Date:** October 22, 2025

## 🎉 Major New Features

### 1. Model Hooks and Signals System
Extensible lifecycle hooks for model events with both class methods and global signals.

**Features:**
- `pre_save` / `post_save` hooks for create and update operations
- `pre_update` / `post_update` hooks for update-specific logic
- `pre_delete` / `post_delete` hooks for deletion operations
- Global signal system with `@receiver` decorator
- Automatic hook triggering in CRUD operations

**Example:**
```python
from fastapi_orm import Model, get_signals, receiver

class User(Model):
    __tablename__ = "users"
    
    username: str = StringField(max_length=100)
    
    @classmethod
    async def pre_save_hook(cls, instance, **kwargs):
        # Called before save
        print(f"About to save: {instance.username}")
    
    @classmethod
    async def post_save_hook(cls, instance, created, **kwargs):
        # Called after save
        if created:
            # Send welcome email, create audit log, etc.
            print(f"New user created: {instance.username}")

# Global signals
signals = get_signals()

@receiver(signals.post_save, sender=User)
async def on_user_saved(sender, instance, created, **kwargs):
    if created:
        await send_welcome_email(instance.email)
```

### 2. Advanced Index Management
Comprehensive indexing utilities for optimal database performance.

**Features:**
- Composite indexes on multiple columns
- Partial/filtered indexes with WHERE conditions
- PostgreSQL-specific indexes (GIN, GIST, HASH, BTREE)
- Covering indexes (index-only scans)
- Fluent interface with `Index` class

**Example:**
```python
from fastapi_orm import create_index, create_partial_index, create_gin_index

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(max_length=255)
    username: str = StringField(max_length=100)
    is_active: bool = BooleanField(default=True)
    tags = ArrayField(nullable=True)
    
    __table_args__ = (
        # Composite index
        create_index("idx_email_username", email, username),
        
        # Partial index - only index active users
        create_partial_index(
            "idx_active_username",
            username,
            condition=is_active == True,
            unique=True
        ),
        
        # GIN index for array operations
        create_gin_index("idx_user_tags", tags),
    )
```

### 3. JSON Field Query Operators
PostgreSQL JSON/JSONB query operators for powerful JSON data querying.

**Features:**
- Containment operations (`@>`, `<@`)
- Key existence checks (`?`, `?|`, `?&`)
- JSON path queries
- Type-safe operator classes

**Example:**
```python
from fastapi_orm import json_contains, json_has_key, json_path

class User(Model):
    __tablename__ = "users"
    
    metadata = JSONField(nullable=True)
    settings = JSONField(nullable=True)

# Find users with premium subscription
users = await User.filter_by(
    session,
    metadata=json_contains({"subscription": "premium"})
)

# Find users who have set a profile picture
users = await User.filter_by(
    session,
    metadata=json_has_key("profile_picture")
)

# Query nested JSON path
users = await User.filter_by(
    session,
    settings=json_path("theme.mode", "dark")
)
```

### 4. Full-Text Search Support
PostgreSQL full-text search capabilities with ranking and highlighting.

**Features:**
- Text search vector columns
- Search queries with relevance ranking
- Language-specific search configuration
- Search result highlighting
- Automatic trigger generation for search vector updates

**Example:**
```python
from fastapi_orm import (
    create_search_vector,
    FullTextSearchMixin,
    create_search_trigger
)

class Article(Model, FullTextSearchMixin):
    __tablename__ = "articles"
    
    title: str = StringField(max_length=200)
    content: str = TextField()
    search_vector = create_search_vector('title', 'content')
    
    __table_args__ = (
        Index('idx_article_search', search_vector, postgresql_using='gin'),
    )

# Search articles
results = await Article.search(
    session,
    "python & (fastapi | django)",
    rank_threshold=0.1,
    limit=10
)

for article, rank in results:
    print(f"{article.title} (relevance: {rank})")
```

### 5. Group By and Aggregations
Advanced aggregation queries with GROUP BY and HAVING support.

**Features:**
- Multiple field grouping
- Aggregate functions (COUNT, SUM, AVG, MAX, MIN)
- HAVING clause support
- Fluent query builder
- `AggregationMixin` for models

**Example:**
```python
from fastapi_orm import AggregationMixin

class Post(Model, AggregationMixin):
    __tablename__ = "posts"
    
    author_id: int = IntegerField()
    views: int = IntegerField(default=0)
    published: bool = BooleanField(default=False)

# Group by author and count posts
results = await Post.group_by(
    session,
    'author_id',
    aggregates={
        'post_count': 'count',
        'total_views': ('sum', 'views'),
        'avg_views': ('avg', 'views')
    },
    having={'post_count__gt': 10},  # Only authors with >10 posts
    order_by=['-total_views']
)

for row in results:
    print(f"Author {row['author_id']}: {row['post_count']} posts, {row['total_views']} total views")
```

### 6. Abstract Model Support
Base classes for model inheritance and shared behavior.

**Features:**
- Abstract models that don't create tables
- Field inheritance across models
- Shared method inheritance
- Helper functions for creating abstract models

**Example:**
```python
from fastapi_orm import AbstractModel

class TimestampedModel(AbstractModel):
    """All models inheriting this will have timestamps"""
    __abstract__ = True
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)

class BaseContent(AbstractModel):
    """Abstract base for all content types"""
    __abstract__ = True
    
    title: str = StringField(max_length=200)
    slug: str = StringField(max_length=200, unique=True)
    
    @classmethod
    async def get_by_slug(cls, session, slug: str):
        return await cls.get_by(session, slug=slug)

class Article(BaseContent, TimestampedModel):
    __tablename__ = "articles"
    
    content: str = TextField()
    # Inherits: title, slug, created_at, updated_at, get_by_slug()

class Page(BaseContent, TimestampedModel):
    __tablename__ = "pages"
    
    body: str = TextField()
    # Also inherits same fields and methods
```

### 7. Database Resilience and Retry Logic
Automatic retry mechanisms with exponential backoff and circuit breaker pattern.

**Features:**
- Exponential backoff with jitter
- Configurable retry attempts
- Circuit breaker to prevent cascading failures
- Transient error detection
- Database health check utilities

**Example:**
```python
from fastapi_orm import with_retry, resilient_connect, wait_for_database

# Decorator for automatic retry
@with_retry(max_attempts=3)
async def create_user(session, username, email):
    return await User.create(session, username=username, email=email)

# Usage - automatically retries on transient errors
user = await create_user(session, "john", "john@example.com")

# Wait for database to be ready
db = Database("postgresql+asyncpg://...")
if await wait_for_database(db, timeout=30):
    print("Database ready!")

# Resilient connection with retry
await resilient_connect(db, max_attempts=5)
```

### 8. Query Performance Monitoring
The existing QueryMonitor was already available in v0.3.0, now documented as part of the comprehensive feature set.

## 📚 API Additions

### New Modules
- `fastapi_orm.hooks` - Model hooks and signals system
- `fastapi_orm.indexes` - Advanced index management
- `fastapi_orm.json_ops` - JSON field query operators  
- `fastapi_orm.fulltext` - Full-text search support
- `fastapi_orm.aggregations` - Group by and aggregations
- `fastapi_orm.abstract` - Abstract model support
- `fastapi_orm.resilience` - Connection retry and resilience

### New Exports
**Hooks:**
- `HooksMixin`
- `get_signals()`
- `receiver()`
- `Signal`

**Indexes:**
- `Index`
- `create_index()`
- `create_partial_index()`
- `create_gin_index()`
- `create_btree_index()`
- `create_hash_index()`
- `create_covering_index()`
- `indexes()`

**JSON Operations:**
- `json_contains()`
- `json_contained_by()`
- `json_has_key()`
- `json_has_any_key()`
- `json_has_all_keys()`
- `json_path()`
- `json_path_exists()`

**Full-Text Search:**
- `create_search_vector()`
- `ts_query()`
- `ts_rank()`
- `ts_headline()`
- `SearchQuery`
- `create_search_trigger()`
- `FullTextSearchMixin`

**Resilience:**
- `RetryConfig`
- `CircuitBreaker`
- `get_circuit_breaker()`
- `with_retry()`
- `resilient_connect()`
- `wait_for_database()`

**Abstract Models:**
- `AbstractModel`
- `create_abstract_model()`

**Aggregations:**
- `AggregateQuery`
- `AggregationMixin`

## 🔄 Breaking Changes
None - this release is fully backward compatible with v0.4.0.

## 🐛 Bug Fixes
- Improved type hints throughout the codebase
- Fixed edge cases in field validation

## 📈 Performance Improvements
- Optimized hook triggering mechanism
- Reduced overhead in CRUD operations
- Better query building performance

## 🎯 Coming Soon
Future features being considered:
- GraphQL integration
- Real-time subscriptions
- Advanced caching strategies
- Multi-tenancy support
- Audit logging utilities

## 📝 Notes
All new features are optional and can be adopted incrementally. Existing code continues to work without modifications.

## 🙏 Acknowledgments
Built on top of:
- SQLAlchemy 2.x (async ORM foundation)
- Pydantic v2 (data validation)
- FastAPI (web framework)
- PostgreSQL (advanced database features)

---

For detailed documentation and examples, see:
- [README.md](README.md) - Main documentation
- [FEATURES.md](FEATURES.md) - Feature details
- [examples/](examples/) - Code examples
