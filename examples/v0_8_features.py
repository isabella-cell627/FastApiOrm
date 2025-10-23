"""
FastAPI ORM v0.8.0 Features Demo

This file demonstrates all the new features added in version 0.8.0:
1. CLI Tools & Code Generation
2. Model Factories for Test Data
3. Advanced Validation System
4. Read Replica Support
5. Polymorphic Relationships
6. Enhanced Migration Tools
"""

import asyncio
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession

# Import v0.8.0 features
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    TextField,
    DateTimeField,
    # Factories
    ModelFactory,
    Faker,
    Sequence,
    LazyAttribute,
    SubFactory,
    # Validators
    email_validator,
    strong_password,
    min_value,
    max_value,
    length_range,
    # Polymorphic
    PolymorphicMixin,
    GenericForeignKey,
    # Read Replicas
    create_replica_manager,
    with_read_session,
    with_write_session,
    # Migration Tools
    DataMigration,
)

# Database setup
db = Database("sqlite+aiosqlite:///./v08_demo.db")

# ===================================================================
# 1. MODEL DEFINITIONS WITH VALIDATION
# ===================================================================

class User(Model):
    """User model with advanced validation"""
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(
        max_length=100,
        nullable=False,
        unique=True,
        validators=[length_range(3, 50)]
    )
    email: str = StringField(
        max_length=255,
        nullable=False,
        unique=True,
        validators=[email_validator()]
    )
    password: str = StringField(
        max_length=255,
        nullable=False,
        validators=[strong_password(min_length=8)]
    )
    age: int = IntegerField(
        validators=[min_value(18), max_value(120)]
    )
    created_at = DateTimeField(auto_now_add=True)


class Post(Model):
    """Post model"""
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    content: str = TextField(nullable=False)
    author_id: int = IntegerField(nullable=False)
    created_at = DateTimeField(auto_now_add=True)


class Comment(Model, PolymorphicMixin):
    """
    Comment model with polymorphic relationships
    Can comment on Posts, Users, or any other model
    """
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = StringField(max_length=500, nullable=False)
    author_id: int = IntegerField(nullable=False)
    
    # Polymorphic fields
    content_type: str = StringField(max_length=50, nullable=False)
    content_id: int = IntegerField(nullable=False)
    
    # Generic foreign key
    content_object = GenericForeignKey('content_type', 'content_id')
    
    created_at = DateTimeField(auto_now_add=True)


# ===================================================================
# 2. MODEL FACTORIES FOR TEST DATA
# ===================================================================

class UserFactory(ModelFactory):
    """Factory for generating test users"""
    class Meta:
        model = User
    
    username = Faker('user_name')
    email = Faker('email')
    password = "SecurePassword123!"  # In real tests, use a hash
    age = Faker('random_int', min=18, max=80)


class PostFactory(ModelFactory):
    """Factory for generating test posts"""
    class Meta:
        model = Post
    
    title = Faker('sentence')
    content = Faker('paragraph')
    author_id = Sequence(start=1)  # Will be 1, 2, 3, ...


class CommentFactory(ModelFactory):
    """Factory for generating test comments"""
    class Meta:
        model = Comment
    
    content = Faker('sentence')
    author_id = Sequence(start=1)
    content_type = "posts"
    content_id = Sequence(start=1)


# ===================================================================
# 3. DEMONSTRATION FUNCTIONS
# ===================================================================

async def demo_factories(session: AsyncSession):
    """Demonstrate model factories"""
    print("\n=== MODEL FACTORIES DEMO ===\n")
    
    # Create single user
    user = await UserFactory.create(session)
    print(f"Created user: {user.username} ({user.email})")
    
    # Create batch of users
    users = await UserFactory.create_batch(session, 5)
    print(f"Created {len(users)} users in batch")
    
    # Create with overrides
    admin = await UserFactory.create(
        session,
        username="admin",
        email="admin@example.com",
        age=30
    )
    print(f"Created admin: {admin.username}")
    
    # Create posts
    posts = await PostFactory.create_batch(session, 10)
    print(f"Created {len(posts)} posts")


async def demo_validation(session: AsyncSession):
    """Demonstrate advanced validation"""
    print("\n=== VALIDATION DEMO ===\n")
    
    # Valid user
    try:
        valid_user = await User.create(
            session,
            username="validuser",
            email="valid@example.com",
            password="SecurePass123!",
            age=25
        )
        print(f"✓ Valid user created: {valid_user.username}")
    except Exception as e:
        print(f"✗ Validation failed: {e}")
    
    # Invalid email
    try:
        invalid_email = await User.create(
            session,
            username="testuser",
            email="not-an-email",
            password="SecurePass123!",
            age=25
        )
    except Exception as e:
        print(f"✓ Email validation caught invalid email: {type(e).__name__}")
    
    # Invalid password (too short)
    try:
        weak_password = await User.create(
            session,
            username="testuser2",
            email="test2@example.com",
            password="weak",
            age=25
        )
    except Exception as e:
        print(f"✓ Password validation caught weak password: {type(e).__name__}")
    
    # Invalid age (too young)
    try:
        underage = await User.create(
            session,
            username="testuser3",
            email="test3@example.com",
            password="SecurePass123!",
            age=15
        )
    except Exception as e:
        print(f"✓ Age validation caught underage: {type(e).__name__}")


async def demo_polymorphic_relationships(session: AsyncSession):
    """Demonstrate polymorphic relationships"""
    print("\n=== POLYMORPHIC RELATIONSHIPS DEMO ===\n")
    
    # Get a post and user
    post = await Post.get(session, 1)
    user = await User.get(session, 1)
    
    if post and user:
        # Comment on a post
        post_comment = await Comment.create(
            session,
            content="Great post!",
            author_id=1,
            content_type="posts",
            content_id=post.id
        )
        print(f"Created comment on post: {post_comment.content}")
        
        # Get the related object
        related_obj = await post_comment.get_content_object(session)
        print(f"Related object type: {type(related_obj).__name__}")
        
        # Comment on a user (e.g., profile comment)
        user_comment = await Comment.create(
            session,
            content="Nice profile!",
            author_id=2,
            content_type="users",
            content_id=user.id
        )
        print(f"Created comment on user: {user_comment.content}")


async def demo_data_migration(session: AsyncSession):
    """Demonstrate data migration utilities"""
    print("\n=== DATA MIGRATION DEMO ===\n")
    
    # Create data migration helper
    migration = DataMigration(session, User)
    
    # Example: Transform all usernames to lowercase
    updated = await migration.transform(
        lambda user: {'username': user.username.lower()},
        batch_size=10
    )
    print(f"Transformed {updated} usernames to lowercase")
    
    # Example: Add default values
    updated = await migration.add_default_values(
        {'age': 18},
        condition=lambda user: user.age is None
    )
    print(f"Added default age to {updated} users")


# ===================================================================
# 4. FASTAPI APPLICATION
# ===================================================================

app = FastAPI(title="FastAPI ORM v0.8.0 Demo")


@app.on_event("startup")
async def startup():
    """Initialize database"""
    await db.create_tables()
    print("Database initialized")
    
    # Run demonstrations
    async with db.session() as session:
        # Check if we need to seed data
        user_count = await User.count(session)
        
        if user_count == 0:
            print("\nSeeding database with test data...")
            await demo_factories(session)
            await demo_validation(session)
            await demo_polymorphic_relationships(session)
            await demo_data_migration(session)


@app.on_event("shutdown")
async def shutdown():
    """Close database"""
    await db.close()


async def get_db():
    """Database dependency"""
    async for session in db.get_session():
        yield session


# ===================================================================
# 5. API ENDPOINTS
# ===================================================================

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "FastAPI ORM v0.8.0 Features Demo",
        "version": "0.8.0",
        "new_features": [
            "CLI Tools & Code Generation",
            "Model Factories",
            "Advanced Validation",
            "Read Replica Support",
            "Polymorphic Relationships",
            "Enhanced Migration Tools"
        ],
        "endpoints": {
            "users": "/users",
            "posts": "/posts",
            "comments": "/comments",
            "docs": "/docs"
        }
    }


@app.get("/users")
async def list_users(session: AsyncSession = Depends(get_db)):
    """List all users"""
    users = await User.all(session, limit=100)
    return [user.to_response() for user in users]


@app.get("/posts")
async def list_posts(session: AsyncSession = Depends(get_db)):
    """List all posts"""
    posts = await Post.all(session, limit=100)
    return [post.to_response() for post in posts]


@app.get("/comments")
async def list_comments(session: AsyncSession = Depends(get_db)):
    """List all comments"""
    comments = await Comment.all(session, limit=100)
    return [comment.to_response() for comment in comments]


@app.get("/stats")
async def get_stats(session: AsyncSession = Depends(get_db)):
    """Get database statistics"""
    return {
        "users": await User.count(session),
        "posts": await Post.count(session),
        "comments": await Comment.count(session)
    }


# ===================================================================
# 6. CLI DEMONSTRATIONS
# ===================================================================

def demo_cli_usage():
    """
    Examples of CLI commands (run these in terminal):
    
    # Inspect database
    python -m fastapi_orm inspect --database-url "sqlite:///./v08_demo.db"
    
    # Generate models from database
    python -m fastapi_orm generate-models --database-url "sqlite:///./v08_demo.db" --output generated_models.py
    
    # Generate single model
    python -m fastapi_orm generate-models --database-url "sqlite:///./v08_demo.db" --table users --output user_model.py
    
    # Scaffold CRUD endpoints
    python -m fastapi_orm scaffold Product --fields "name:str,price:float,stock:int" --output api_product.py
    
    # Create migration
    python -m fastapi_orm create-migration "Add products table"
    
    # Run migrations
    python -m fastapi_orm upgrade
    """
    pass


if __name__ == "__main__":
    import uvicorn
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         FastAPI ORM v0.8.0 Features Demo                ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  New Features:                                           ║
    ║  • CLI Tools & Code Generation                           ║
    ║  • Model Factories for Test Data                         ║
    ║  • Advanced Validation System                            ║
    ║  • Read Replica Support                                  ║
    ║  • Polymorphic Relationships                             ║
    ║  • Enhanced Migration Tools                              ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Starting server on http://0.0.0.0:5000
    API docs available at http://0.0.0.0:5000/docs
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=5000)
