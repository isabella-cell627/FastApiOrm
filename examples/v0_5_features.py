"""
FastAPI ORM v0.5.0 - New Features Demo

This example demonstrates all the major features added in v0.5.0:
1. Model Hooks and Signals
2. Advanced Indexing
3. Full-Text Search
4. Aggregations and Group By
5. Abstract Models
6. Connection Resilience
"""

import asyncio
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator

from fastapi_orm import (
    Database,
    Model,
    AbstractModel,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    JSONField,
    ArrayField,
    # Hooks
    get_signals,
    receiver,
    # Indexes
    create_index,
    create_partial_index,
    create_gin_index,
    # Full-text search
    create_search_vector,
    FullTextSearchMixin,
    # Aggregations
    AggregationMixin,
    # Resilience
    with_retry,
    resilient_connect,
)
from sqlalchemy import Index

# Initialize database
db = Database("sqlite+aiosqlite:///./demo_v05.db", echo=True)

# Get global signals
signals = get_signals()


# =============================================================================
# 1. ABSTRACT MODELS - Shared base classes
# =============================================================================

class TimestampedModel(AbstractModel):
    """Base model with automatic timestamps"""
    __abstract__ = True
    
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)


class ContentModel(AbstractModel):
    """Base model for content with common fields"""
    __abstract__ = True
    
    title: str = StringField(max_length=200, nullable=False)
    slug: str = StringField(max_length=200, unique=True, nullable=False)
    
    @classmethod
    async def get_by_slug(cls, session, slug: str):
        return await cls.get_by(session, slug=slug)


# =============================================================================
# 2. MODEL HOOKS - Pre/post save, update, delete
# =============================================================================

class User(TimestampedModel):
    """User model with lifecycle hooks"""
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    is_active: bool = BooleanField(default=True)
    metadata = JSONField(nullable=True)
    
    # Advanced indexes
    __table_args__ = (
        # Composite index on email and is_active
        create_index("idx_user_email_active", email, is_active),
        
        # Partial index - only index active users
        create_partial_index(
            "idx_active_username",
            username,
            condition=is_active == True
        ),
    )
    
    # Pre-save hook
    @classmethod
    async def pre_save_hook(cls, instance, **kwargs):
        print(f"⏰ PRE-SAVE: About to save user: {instance.username}")
        # Could: validate data, set defaults, etc.
    
    # Post-save hook
    @classmethod
    async def post_save_hook(cls, instance, created, **kwargs):
        if created:
            print(f"✨ POST-SAVE: New user created: {instance.username}")
            # Could: send welcome email, create audit log, etc.
        else:
            print(f"📝 POST-SAVE: User updated: {instance.username}")
    
    # Pre-delete hook
    @classmethod
    async def pre_delete_hook(cls, instance, **kwargs):
        print(f"⚠️  PRE-DELETE: About to delete user: {instance.username}")
        # Could: archive data, check dependencies, etc.
    
    # Post-delete hook
    @classmethod
    async def post_delete_hook(cls, instance, **kwargs):
        print(f"🗑️  POST-DELETE: User deleted: {instance.username}")


# Global signal handler for User saves
@receiver(signals.post_save, sender=User)
async def on_user_saved(sender, instance, created, **kwargs):
    if created:
        print(f"🔔 SIGNAL: User {instance.username} was created!")


# =============================================================================
# 3. FULL-TEXT SEARCH - PostgreSQL text search
# =============================================================================

class Article(ContentModel, TimestampedModel, FullTextSearchMixin, AggregationMixin):
    """Article with full-text search and aggregation support"""
    __tablename__ = "articles"
    
    id: int = IntegerField(primary_key=True)
    content: str = TextField(nullable=False)
    author_id: int = IntegerField(nullable=False)
    views: int = IntegerField(default=0)
    published: bool = BooleanField(default=False)
    tags = ArrayField(nullable=True)  # PostgreSQL array
    search_vector = create_search_vector('title', 'content')
    
    __table_args__ = (
        # GIN index for full-text search
        Index('idx_article_search', search_vector, postgresql_using='gin'),
        
        # GIN index for array operations
        create_gin_index('idx_article_tags', tags),
    )


# =============================================================================
# 4. AGGREGATIONS - Group by with mixins
# =============================================================================

class Post(TimestampedModel, AggregationMixin):
    """Post model with aggregation support"""
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    author_id: int = IntegerField(nullable=False)
    views: int = IntegerField(default=0)
    likes: int = IntegerField(default=0)
    published: bool = BooleanField(default=False)


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(title="FastAPI ORM v0.5.0 Demo")


@app.on_event("startup")
async def startup():
    """Initialize database with resilience"""
    # Use resilient connection
    await resilient_connect(db, max_attempts=3)
    await db.create_tables()
    print("✅ Database ready!")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in db.get_session():
        yield session


# =============================================================================
# Demo Endpoints
# =============================================================================

@app.get("/")
async def root():
    return {
        "message": "FastAPI ORM v0.5.0 Feature Demo",
        "features": [
            "Model Hooks & Signals",
            "Advanced Indexing",
            "Full-Text Search",
            "Aggregations",
            "Abstract Models",
            "Connection Resilience"
        ]
    }


@app.post("/demo/hooks")
async def demo_hooks(session: AsyncSession = Depends(get_db)):
    """Demonstrate model hooks in action"""
    
    # Create user - triggers pre_save and post_save hooks
    user = await User.create(
        session,
        username="john_doe",
        email="john@example.com",
        metadata={"subscription": "premium"}
    )
    
    # Update user - triggers pre_update and post_update hooks
    await user.update_fields(session, username="jane_doe")
    
    # Delete user - triggers pre_delete and post_delete hooks
    await user.delete(session)
    
    return {"message": "Check console for hook outputs!"}


@app.post("/demo/aggregations")
async def demo_aggregations(session: AsyncSession = Depends(get_db)):
    """Demonstrate GROUP BY aggregations"""
    
    # Create sample posts
    for i in range(1, 6):
        for j in range(1, 4):
            await Post.create(
                session,
                title=f"Post {i}-{j}",
                author_id=i,
                views=i * 10 + j,
                likes=i * 5
            )
    
    await session.commit()
    
    # Group by author and aggregate
    results = await Post.group_by(
        session,
        'author_id',
        aggregates={
            'post_count': 'count',
            'total_views': ('sum', 'views'),
            'avg_views': ('avg', 'views'),
            'max_views': ('max', 'views'),
            'total_likes': ('sum', 'likes')
        },
        having={'post_count__gte': 2},  # Only authors with 2+ posts
        order_by=['-total_views']
    )
    
    return {
        "aggregations": results,
        "description": "Posts grouped by author with aggregates"
    }


@app.post("/demo/resilience")
async def demo_resilience(session: AsyncSession = Depends(get_db)):
    """Demonstrate retry logic"""
    
    # Function with automatic retry
    @with_retry(max_attempts=3)
    async def create_user_with_retry(session, username, email):
        return await User.create(session, username=username, email=email)
    
    try:
        user = await create_user_with_retry(
            session,
            "resilient_user",
            "resilient@example.com"
        )
        await session.commit()
        
        return {
            "message": "User created with retry protection",
            "user": user.to_response()
        }
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Main - Run demo
# =============================================================================

async def run_demos():
    """Run all feature demos"""
    await startup()
    
    async with db.session() as session:
        print("\n" + "="*60)
        print("1. TESTING HOOKS")
        print("="*60)
        
        # Create user (triggers hooks)
        user = await User.create(
            session,
            username="demo_user",
            email="demo@example.com"
        )
        await session.commit()
        
        print("\n" + "="*60)
        print("2. TESTING AGGREGATIONS")
        print("="*60)
        
        # Create posts
        for i in range(1, 4):
            for j in range(1, 4):
                await Post.create(
                    session,
                    title=f"Post {i}-{j}",
                    author_id=i,
                    views=i * 10 + j,
                    likes=i * 5
                )
        await session.commit()
        
        # Aggregate
        results = await Post.group_by(
            session,
            'author_id',
            aggregates={
                'post_count': 'count',
                'total_views': ('sum', 'views')
            }
        )
        
        print("\nAggregation Results:")
        for row in results:
            print(f"  Author {row['author_id']}: {row['post_count']} posts, {row['total_views']} views")
        
        print("\n✅ All demos completed!")


if __name__ == "__main__":
    # Run demos
    asyncio.run(run_demos())
    
    # Or run FastAPI app
    # uvicorn examples.v0_5_features:app --reload
