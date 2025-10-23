# Getting Started with FastAPI ORM

## Introduction

FastAPI ORM is a lightweight, production-ready ORM library built on top of SQLAlchemy 2.x with full async support, automatic Pydantic integration, and intuitive Django-like syntax. It's designed specifically for FastAPI applications, combining the simplicity of Django ORM with the power and flexibility of SQLAlchemy.

## Why FastAPI ORM?

- **Clean Syntax**: Django-like model definitions with minimal boilerplate
- **Fully Async**: Built from the ground up with async/await support
- **Type-Safe**: Full type hints and IDE autocomplete
- **Pydantic Integration**: Automatic conversion to Pydantic models for FastAPI responses
- **Production-Ready**: Includes caching, transactions, audit logging, and more

## Installation

### Core Installation

```bash
pip install sqlalchemy>=2.0.0 fastapi>=0.100.0 pydantic>=2.0.0 uvicorn>=0.20.0
pip install asyncpg>=0.29.0 aiosqlite>=0.19.0 alembic>=1.12.0
```

### Optional Dependencies

For advanced features, install these additional packages:

```bash
# Distributed caching with Redis
pip install redis>=5.0.0

# WebSocket support
pip install websockets>=12.0

# GraphQL integration
pip install strawberry-graphql

# File upload handling
pip install aiofiles boto3 pillow

# Testing and development
pip install pytest pytest-asyncio faker
```

## Quick Start

### Step 1: Define Your Models

Create a file `models.py`:

```python
from fastapi_orm import (
    Model,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    OneToMany,
    ManyToOne,
)

class User(Model):
    __tablename__ = "users"

    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    is_active: bool = BooleanField(default=True)
    created_at = DateTimeField(auto_now_add=True)
    
    posts = OneToMany("Post", back_populates="author")


class Post(Model):
    __tablename__ = "posts"

    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    published: bool = BooleanField(default=False)
    author_id: int = ForeignKeyField("users", nullable=False)
    created_at = DateTimeField(auto_now_add=True)
    
    author = ManyToOne("User", back_populates="posts")
```

### Step 2: Initialize the Database

Create a file `database.py`:

```python
from fastapi_orm import Database

# For SQLite (development)
db = Database("sqlite+aiosqlite:///./app.db", echo=True)

# For PostgreSQL (production)
# db = Database("postgresql+asyncpg://user:password@localhost/dbname")

# For MySQL
# db = Database("mysql+aiomysql://user:password@localhost/dbname")
```

### Step 3: Create Your FastAPI Application

Create a file `main.py`:

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
from pydantic import BaseModel

from database import db
from models import User, Post

app = FastAPI(title="My API")

# Dependency for database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in db.get_session():
        yield session

# Startup event to create tables
@app.on_event("startup")
async def startup():
    await db.create_tables()
    print("Database tables created successfully!")

# Shutdown event to close database
@app.on_event("shutdown")
async def shutdown():
    await db.close()

# Pydantic models for request validation
class UserCreate(BaseModel):
    username: str
    email: str
    is_active: bool = True

class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = False
    author_id: int

# API Endpoints
@app.get("/")
async def root():
    return {"message": "Welcome to FastAPI ORM!"}

@app.post("/users", status_code=201)
async def create_user(user_data: UserCreate, session: AsyncSession = Depends(get_db)):
    user = await User.create(session, **user_data.model_dump())
    return user.to_response()

@app.get("/users")
async def list_users(
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db)
):
    users = await User.all(session, limit=limit, offset=offset)
    return [user.to_response() for user in users]

@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_response()

@app.put("/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_db)
):
    user = await User.update_by_id(session, user_id, **user_data.model_dump())
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_response()

@app.delete("/users/{user_id}", status_code=204)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_db)):
    deleted = await User.delete_by_id(session, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return None

@app.post("/posts", status_code=201)
async def create_post(post_data: PostCreate, session: AsyncSession = Depends(get_db)):
    post = await Post.create(session, **post_data.model_dump())
    return post.to_response()

@app.get("/posts")
async def list_posts(
    published: bool = None,
    session: AsyncSession = Depends(get_db)
):
    if published is not None:
        posts = await Post.filter(session, published=published)
    else:
        posts = await Post.all(session)
    return [post.to_response() for post in posts]
```

### Step 4: Run Your Application

```bash
uvicorn main:app --reload
```

Visit `http://localhost:8000/docs` to see your interactive API documentation!

## Basic CRUD Operations

### Create

```python
# Single record
user = await User.create(session, username="john", email="john@example.com")

# With relationships
post = await Post.create(
    session,
    title="My First Post",
    content="Hello World!",
    author_id=user.id
)
```

### Read

```python
# Get by primary key
user = await User.get(session, 1)

# Get all records
users = await User.all(session)

# Filter records
active_users = await User.filter(session, is_active=True)

# Get specific columns
users = await User.all(session, columns=["id", "username"])
```

### Update

```python
# Update instance
user = await User.get(session, 1)
await user.update_fields(session, email="newemail@example.com")

# Update by ID
user = await User.update_by_id(session, 1, email="newemail@example.com")

# Update multiple records
await User.filter(session, is_active=False).update(is_active=True)
```

### Delete

```python
# Delete instance
user = await User.get(session, 1)
await user.delete(session)

# Delete by ID
deleted = await User.delete_by_id(session, 1)

# Delete filtered records
await User.filter(session, is_active=False).delete()
```

## Working with Relationships

### One-to-Many

```python
# Get user with posts
user = await User.get(session, 1)
posts = user.posts  # Access related posts

# Create post for user
new_post = await Post.create(
    session,
    title="New Post",
    content="Content",
    author_id=user.id
)
```

### Many-to-One

```python
# Get post with author
post = await Post.get(session, 1)
author = post.author  # Access related user
```

### Many-to-Many

```python
from fastapi_orm import ManyToMany, create_association_table, Base

# Create association table
post_tag_association = create_association_table(
    "post_tags",
    "posts",
    "tags",
    Base
)

class Post(Model):
    __tablename__ = "posts"
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    
    tags = ManyToMany("Tag", secondary=post_tag_association, back_populates="posts")

class Tag(Model):
    __tablename__ = "tags"
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=50)
    
    posts = ManyToMany("Post", secondary=post_tag_association, back_populates="tags")

# Usage
post = await Post.get(session, 1)
tag = await Tag.get(session, 1)
post.tags.append(tag)
await session.commit()
```

## Database Configuration

### Connection String Format

```python
# SQLite
db = Database("sqlite+aiosqlite:///./app.db")

# PostgreSQL
db = Database("postgresql+asyncpg://user:password@host:port/database")

# MySQL
db = Database("mysql+aiomysql://user:password@host:port/database")
```

### Database Options

```python
db = Database(
    "postgresql+asyncpg://user:password@localhost/dbname",
    echo=True,  # Log SQL statements
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Maximum overflow connections
    pool_timeout=30,  # Timeout for getting connection
    pool_recycle=3600,  # Recycle connections after 1 hour
)
```

### Create and Drop Tables

```python
# Create all tables
await db.create_tables()

# Drop all tables
await db.drop_tables()

# Create specific tables
from models import User, Post
await db.create_tables([User, Post])
```

## Automatic Pydantic Integration

Every model automatically has a `to_response()` method that converts the model to a Pydantic-compatible dictionary:

```python
user = await User.get(session, 1)
response_data = user.to_response()
# Returns: {"id": 1, "username": "john", "email": "john@example.com", ...}

# Perfect for FastAPI responses
@app.get("/users/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_db)):
    user = await User.get(session, user_id)
    return user.to_response()
```

## Next Steps

- Learn about [advanced querying](02-advanced-querying.md)
- Explore [pagination and filtering](03-pagination.md)
- Discover [caching strategies](08-caching.md)
- Set up [database migrations](16-migrations.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **GitHub**: https://github.com/Alqudimi
- **Repository**: https://github.com/Alqudimi/FastApiOrm

For issues or questions, please visit the GitHub repository or contact the developer.
