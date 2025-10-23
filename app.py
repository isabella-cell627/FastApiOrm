from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, AsyncGenerator
from pydantic import BaseModel

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
    create_association_table,
    ManyToMany,
    Base,
)

app = FastAPI(
    title="FastAPI ORM Demo",
    description="A demonstration of the FastAPI-native ORM library",
    version="1.0.0"
)

db = Database("sqlite+aiosqlite:///./demo.db", echo=True)

post_tag_association = create_association_table(
    "post_tags",
    "posts",
    "tags",
    Base
)


@app.on_event("startup")
async def startup():
    await db.create_tables()
    print("Database tables created successfully!")


@app.on_event("shutdown")
async def shutdown():
    await db.close()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in db.get_session():
        yield session


class User(Model):
    __tablename__ = "users"

    id: int = IntegerField(primary_key=True)  # type: ignore
    username: str = StringField(max_length=100, unique=True, nullable=False)  # type: ignore
    email: str = StringField(max_length=255, unique=True, nullable=False)  # type: ignore
    bio: str = TextField(nullable=True)  # type: ignore
    is_active: bool = BooleanField(default=True)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)
    
    posts = OneToMany("Post", back_populates="author")
    comments = OneToMany("Comment", back_populates="user")


class Post(Model):
    __tablename__ = "posts"

    id: int = IntegerField(primary_key=True)  # type: ignore
    title: str = StringField(max_length=200, nullable=False)  # type: ignore
    content: str = TextField(nullable=False)  # type: ignore
    published: bool = BooleanField(default=False)  # type: ignore
    author_id: int = ForeignKeyField("users", nullable=False)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)
    
    author = ManyToOne("User", back_populates="posts")
    comments = OneToMany("Comment", back_populates="post")
    tags = ManyToMany("Tag", secondary=post_tag_association, back_populates="posts")


class Tag(Model):
    __tablename__ = "tags"

    id: int = IntegerField(primary_key=True)  # type: ignore
    name: str = StringField(max_length=50, unique=True, nullable=False)  # type: ignore
    
    posts = ManyToMany("Post", secondary=post_tag_association, back_populates="tags")


class Comment(Model):
    __tablename__ = "comments"

    id: int = IntegerField(primary_key=True)  # type: ignore
    content: str = TextField(nullable=False)  # type: ignore
    user_id: int = ForeignKeyField("users", nullable=False)  # type: ignore
    post_id: int = ForeignKeyField("posts", nullable=False)  # type: ignore
    created_at = DateTimeField(auto_now_add=True)
    
    user = ManyToOne("User", back_populates="comments")
    post = ManyToOne("Post", back_populates="comments")


class UserCreate(BaseModel):
    username: str
    email: str
    bio: Optional[str] = None
    is_active: bool = True


class PostCreate(BaseModel):
    title: str
    content: str
    published: bool = False
    author_id: int


class CommentCreate(BaseModel):
    content: str
    user_id: int
    post_id: int


class TagCreate(BaseModel):
    name: str


@app.get("/")
async def root():
    return {
        "message": "Welcome to FastAPI ORM Demo!",
        "endpoints": {
            "users": "/users",
            "posts": "/posts",
            "comments": "/comments",
            "tags": "/tags",
            "docs": "/docs"
        }
    }


@app.post("/users", status_code=201)
async def create_user(user_data: UserCreate, session: AsyncSession = Depends(get_db)):
    try:
        user = await User.create(session, **user_data.model_dump())
        return user.to_response()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/users")
async def get_users(
    limit: Optional[int] = 100,
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
    try:
        post = await Post.create(session, **post_data.model_dump())
        return post.to_response()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/posts")
async def get_posts(
    limit: Optional[int] = 100,
    offset: int = 0,
    published: Optional[bool] = None,
    session: AsyncSession = Depends(get_db)
):
    if published is not None:
        posts = await Post.filter(session, published=published)
    else:
        posts = await Post.all(session, limit=limit, offset=offset)
    return [post.to_response() for post in posts]


@app.get("/posts/{post_id}")
async def get_post(post_id: int, session: AsyncSession = Depends(get_db)):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post.to_response()


@app.post("/comments", status_code=201)
async def create_comment(comment_data: CommentCreate, session: AsyncSession = Depends(get_db)):
    try:
        comment = await Comment.create(session, **comment_data.model_dump())
        return comment.to_response()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/comments")
async def get_comments(
    post_id: Optional[int] = None,
    user_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db)
):
    if post_id:
        comments = await Comment.filter(session, post_id=post_id)
    elif user_id:
        comments = await Comment.filter(session, user_id=user_id)
    else:
        comments = await Comment.all(session)
    return [comment.to_response() for comment in comments]


@app.post("/tags", status_code=201)
async def create_tag(tag_data: TagCreate, session: AsyncSession = Depends(get_db)):
    try:
        tag = await Tag.create(session, **tag_data.model_dump())
        return tag.to_response()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/tags")
async def get_tags(session: AsyncSession = Depends(get_db)):
    tags = await Tag.all(session)
    return [tag.to_response() for tag in tags]


@app.get("/tags/{tag_id}")
async def get_tag(tag_id: int, session: AsyncSession = Depends(get_db)):
    tag = await Tag.get(session, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag.to_response()


@app.post("/posts/{post_id}/tags/{tag_id}", status_code=200)
async def add_tag_to_post(
    post_id: int,
    tag_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    tag = await Tag.get(session, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag not in post.tags:
        post.tags.append(tag)
        await session.commit()
    
    return {
        "message": f"Tag '{tag.name}' added to post '{post.title}'",
        "post_id": post.id,
        "tag_id": tag.id
    }


@app.delete("/posts/{post_id}/tags/{tag_id}", status_code=200)
async def remove_tag_from_post(
    post_id: int,
    tag_id: int,
    session: AsyncSession = Depends(get_db)
):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    tag = await Tag.get(session, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    
    if tag in post.tags:
        post.tags.remove(tag)
        await session.commit()
    
    return {
        "message": f"Tag '{tag.name}' removed from post '{post.title}'",
        "post_id": post.id,
        "tag_id": tag.id
    }


@app.get("/posts/{post_id}/tags")
async def get_post_tags(post_id: int, session: AsyncSession = Depends(get_db)):
    post = await Post.get(session, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return {
        "post_id": post.id,
        "title": post.title,
        "tags": [{"id": tag.id, "name": tag.name} for tag in post.tags]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
