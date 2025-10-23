import asyncio
from fastapi_orm import (
    Database,
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


async def main():
    db = Database("sqlite+aiosqlite:///./example.db", echo=True)
    
    await db.create_tables()
    
    async with db.session() as session:
        user = await User.create(
            session,
            username="john_doe",
            email="john@example.com",
            is_active=True
        )
        print(f"Created user: {user.username} (ID: {user.id})")
        
        post = await Post.create(
            session,
            title="My First Post",
            content="This is the content of my first post!",
            published=True,
            author_id=user.id
        )
        print(f"Created post: {post.title} (ID: {post.id})")
    
    async with db.session() as session:
        user = await User.get(session, 1)
        if user:
            print(f"\nRetrieved user: {user.username}")
            print(f"User dict: {user.to_dict()}")
            
            response = user.to_response()
            print(f"User response model: {response.model_dump()}")
    
    async with db.session() as session:
        all_users = await User.all(session)
        print(f"\nTotal users: {len(all_users)}")
        
        all_posts = await Post.all(session)
        print(f"Total posts: {len(all_posts)}")
    
    async with db.session() as session:
        user = await User.get(session, 1)
        if user:
            await user.update_fields(session, username="jane_doe")
            print(f"\nUpdated username to: {user.username}")
    
    await db.close()
    print("\nExample completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
