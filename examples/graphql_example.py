"""
Example demonstrating GraphQL integration with FastAPI ORM.

This example shows how to automatically generate a complete GraphQL API
from your ORM models with queries, mutations, and type safety.

Requirements:
    pip install strawberry-graphql
"""

from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from strawberry.fastapi import GraphQLRouter

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    DateTimeField,
    ForeignKeyField,
    ManyToOne,
    OneToMany,
)
from fastapi_orm.graphql_integration import GraphQLManager, create_graphql_context


app = FastAPI(title="GraphQL Blog API")
db = Database("sqlite+aiosqlite:///./blog.db", echo=True)


class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True, nullable=False)
    email: str = StringField(max_length=255, unique=True, nullable=False)
    bio: str = TextField(nullable=True)
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


@app.on_event("startup")
async def startup():
    await db.create_tables()
    print("✓ Database tables created")


async def get_session():
    async for session in db.get_session():
        yield session


async def get_graphql_context(session: AsyncSession = Depends(get_session)):
    """Provide database session to GraphQL context"""
    return create_graphql_context(session)


gql = GraphQLManager()
gql.register_model(User, exclude_fields=[], read_only_fields=["id", "created_at"])
gql.register_model(Post, exclude_fields=[], read_only_fields=["id", "created_at"])

schema = gql.create_schema()

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_graphql_context,
)

app.include_router(graphql_app, prefix="/graphql")


@app.get("/")
async def root():
    return {
        "message": "GraphQL Blog API",
        "graphql_endpoint": "/graphql",
        "graphql_playground": "/graphql (GET request from browser)"
    }


"""
Example GraphQL Queries:

# Get user by ID
query {
  getUser(id: 1) {
    id
    username
    email
    bio
    isActive
    createdAt
  }
}

# List all users
query {
  listUsers(limit: 10, offset: 0) {
    id
    username
    email
  }
}

# Count users
query {
  countUsers
}

# List posts
query {
  listPosts(limit: 5) {
    id
    title
    content
    published
    authorId
    createdAt
  }
}

Example GraphQL Mutations:

# Create user
mutation {
  createUser(input: {
    username: "johndoe"
    email: "john@example.com"
    bio: "Software developer"
    isActive: true
  }) {
    id
    username
    email
  }
}

# Update user
mutation {
  updateUser(id: 1, input: {
    bio: "Updated bio"
    isActive: true
  }) {
    id
    username
    bio
  }
}

# Create post
mutation {
  createPost(input: {
    title: "My First Post"
    content: "This is the content of my first post"
    published: true
    authorId: 1
  }) {
    id
    title
    authorId
  }
}

# Delete post
mutation {
  deletePost(id: 1)
}
"""


if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("GraphQL Blog API Server")
    print("="*50)
    print("\nGraphQL Playground: http://localhost:5000/graphql")
    print("Root endpoint: http://localhost:5000/\n")
    uvicorn.run(app, host="0.0.0.0", port=5000)
