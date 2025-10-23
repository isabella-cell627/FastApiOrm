# Relationships

## Overview

FastAPI ORM supports three types of relationships between models:
- **One-to-Many**: One record relates to many records (e.g., User has many Posts)
- **Many-to-One**: Many records relate to one record (e.g., Post belongs to User)
- **Many-to-Many**: Many records relate to many records (e.g., Posts have many Tags)

## One-to-Many Relationships

### Defining One-to-Many

```python
from fastapi_orm import Model, IntegerField, StringField, ForeignKeyField, OneToMany, ManyToOne

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    # One user has many posts
    posts = OneToMany("Post", back_populates="author")
    comments = OneToMany("Comment", back_populates="user")

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    author_id: int = ForeignKeyField("users", nullable=False)
    
    # Many posts belong to one user
    author = ManyToOne("User", back_populates="posts")
    comments = OneToMany("Comment", back_populates="post")

class Comment(Model):
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = StringField(max_length=500)
    user_id: int = ForeignKeyField("users", nullable=False)
    post_id: int = ForeignKeyField("posts", nullable=False)
    
    user = ManyToOne("User", back_populates="comments")
    post = ManyToOne("Post", back_populates="comments")
```

### Using One-to-Many Relationships

```python
# Create user and posts
user = await User.create(session, username="john")

post1 = await Post.create(
    session,
    title="First Post",
    author_id=user.id
)

post2 = await Post.create(
    session,
    title="Second Post",
    author_id=user.id
)

# Access related posts
user_posts = user.posts  # List of Post objects
print(f"User has {len(user_posts)} posts")

for post in user_posts:
    print(f"- {post.title}")
```

### Cascade Delete

```python
from fastapi_orm import ForeignKeyField

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    
    # Cascade delete: delete posts when user is deleted
    author_id: int = ForeignKeyField(
        "users",
        nullable=False,
        on_delete="CASCADE"  # CASCADE, SET NULL, RESTRICT, etc.
    )
    
    author = ManyToOne("User", back_populates="posts")

# When user is deleted, all their posts are also deleted
user = await User.get(session, 1)
await user.delete(session)  # All user's posts are deleted too
```

## Many-to-One Relationships

### Defining Many-to-One

```python
class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    author_id: int = ForeignKeyField("users", nullable=False)
    
    # Many posts belong to one author
    author = ManyToOne("User", back_populates="posts")
```

### Using Many-to-One Relationships

```python
# Get post with author information
post = await Post.get(session, 1)
author = post.author  # User object

print(f"Post: {post.title}")
print(f"Author: {author.username}")

# Create post with author
user = await User.get(session, 1)
new_post = await Post.create(
    session,
    title="New Post",
    author_id=user.id
)
```

## Many-to-Many Relationships

### Defining Many-to-Many

First, create an association table:

```python
from fastapi_orm import ManyToMany, create_association_table, Base

# Create the association table
post_tag_association = create_association_table(
    "post_tags",     # Table name
    "posts",         # First table
    "tags",          # Second table
    Base
)

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    
    # Posts can have many tags
    tags = ManyToMany("Tag", secondary=post_tag_association, back_populates="posts")

class Tag(Model):
    __tablename__ = "tags"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=50, unique=True)
    
    # Tags can be on many posts
    posts = ManyToMany("Post", secondary=post_tag_association, back_populates="tags")
```

### Using Many-to-Many Relationships

```python
# Create posts and tags
post = await Post.create(session, title="Python Tutorial")
tag1 = await Tag.create(session, name="python")
tag2 = await Tag.create(session, name="tutorial")

# Add tags to post
post.tags.append(tag1)
post.tags.append(tag2)
await session.commit()

# Get all tags for a post
print(f"Post '{post.title}' has tags:")
for tag in post.tags:
    print(f"- {tag.name}")

# Get all posts for a tag
tag = await Tag.get(session, 1)
print(f"Tag '{tag.name}' is on posts:")
for p in tag.posts:
    print(f"- {p.title}")

# Remove tag from post
post.tags.remove(tag1)
await session.commit()

# Clear all tags
post.tags.clear()
await session.commit()
```

### FastAPI Example with Many-to-Many

```python
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

app = FastAPI()

@app.post("/posts/{post_id}/tags/{tag_id}")
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

@app.delete("/posts/{post_id}/tags/{tag_id}")
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
    
    return {"message": f"Tag removed from post"}

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
```

## Self-Referential Relationships

### Tree Structure (Parent-Child)

```python
class Category(Model):
    __tablename__ = "categories"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    parent_id: int = ForeignKeyField("categories", nullable=True)
    
    # Self-referential relationships
    parent = ManyToOne("Category", back_populates="children")
    children = OneToMany("Category", back_populates="parent")

# Usage
root = await Category.create(session, name="Electronics")
laptop = await Category.create(session, name="Laptops", parent_id=root.id)
gaming = await Category.create(session, name="Gaming Laptops", parent_id=laptop.id)

# Navigate tree
category = await Category.get(session, gaming.id)
print(category.parent.name)  # "Laptops"
print(category.parent.parent.name)  # "Electronics"
print(root.children)  # [laptop]
```

### User Following System

```python
from fastapi_orm import ManyToMany, create_association_table, Base

# Create follower association table
follower_association = create_association_table(
    "followers",
    "users",
    "users",
    Base,
    first_column="follower_id",
    second_column="following_id"
)

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    # Users following this user
    followers = ManyToMany(
        "User",
        secondary=follower_association,
        back_populates="following"
    )
    
    # Users this user is following
    following = ManyToMany(
        "User",
        secondary=follower_association,
        back_populates="followers"
    )

# Usage
user1 = await User.create(session, username="alice")
user2 = await User.create(session, username="bob")

# Alice follows Bob
user1.following.append(user2)
await session.commit()

# Check relationships
print(f"{user1.username} is following {len(user1.following)} users")
print(f"{user2.username} has {len(user2.followers)} followers")
```

## Eager Loading

### Load Related Data

```python
from sqlalchemy.orm import selectinload

# Load posts with their authors
stmt = select(Post).options(selectinload(Post.author))
result = await session.execute(stmt)
posts = result.scalars().all()

for post in posts:
    # No additional query needed - author is already loaded
    print(f"{post.title} by {post.author.username}")
```

### Load Multiple Relationships

```python
from sqlalchemy.orm import selectinload

# Load posts with authors and tags
stmt = select(Post).options(
    selectinload(Post.author),
    selectinload(Post.tags)
)
result = await session.execute(stmt)
posts = result.scalars().all()

for post in posts:
    print(f"Post: {post.title}")
    print(f"Author: {post.author.username}")
    print(f"Tags: {', '.join(tag.name for tag in post.tags)}")
```

## Advanced Relationship Patterns

### Through Model (Custom Association)

```python
class UserGroup(Model):
    __tablename__ = "user_groups"
    
    id: int = IntegerField(primary_key=True)
    user_id: int = ForeignKeyField("users", nullable=False)
    group_id: int = ForeignKeyField("groups", nullable=False)
    role: str = StringField(max_length=50, default="member")
    joined_at = DateTimeField(auto_now_add=True)
    
    user = ManyToOne("User", back_populates="group_memberships")
    group = ManyToOne("Group", back_populates="user_memberships")

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    group_memberships = OneToMany("UserGroup", back_populates="user")

class Group(Model):
    __tablename__ = "groups"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    
    user_memberships = OneToMany("UserGroup", back_populates="group")

# Usage
user = await User.create(session, username="john")
group = await Group.create(session, name="Developers")

membership = await UserGroup.create(
    session,
    user_id=user.id,
    group_id=group.id,
    role="admin"
)

# Get all groups for a user with roles
for membership in user.group_memberships:
    group = membership.group
    print(f"{user.username} is {membership.role} in {group.name}")
```

### Polymorphic Relationships

```python
from fastapi_orm import PolymorphicMixin

class Comment(Model, PolymorphicMixin):
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = StringField(max_length=500)
    
    # Can comment on different types of content
    commentable_type: str = StringField(max_length=50)  # "Post", "Photo", etc.
    commentable_id: int = IntegerField()

# Usage with helper methods provided by PolymorphicMixin
comment = await Comment.create(
    session,
    content="Great post!",
    commentable_type="Post",
    commentable_id=1
)
```

## Best Practices

1. **Use appropriate cascade options**: Choose CASCADE, SET NULL, or RESTRICT based on your needs
2. **Define both sides**: Always define relationships on both models
3. **Use back_populates**: Keep relationships synchronized
4. **Eager load when needed**: Prevent N+1 query problems
5. **Index foreign keys**: FastAPI ORM indexes them by default
6. **Use nullable wisely**: Make foreign keys nullable only when appropriate

## Complete Example

```python
from fastapi_orm import (
    Model,
    IntegerField,
    StringField,
    TextField,
    DateTimeField,
    ForeignKeyField,
    OneToMany,
    ManyToOne,
    ManyToMany,
    create_association_table,
    Base,
)

# Association table for many-to-many
post_tag_association = create_association_table(
    "post_tags",
    "posts",
    "tags",
    Base
)

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, unique=True)
    
    # One-to-Many: User has many posts
    posts = OneToMany("Post", back_populates="author")
    # One-to-Many: User has many comments
    comments = OneToMany("Comment", back_populates="user")

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    content: str = TextField()
    created_at = DateTimeField(auto_now_add=True)
    
    # Many-to-One: Post belongs to one author
    author_id: int = ForeignKeyField("users", nullable=False, on_delete="CASCADE")
    author = ManyToOne("User", back_populates="posts")
    
    # One-to-Many: Post has many comments
    comments = OneToMany("Comment", back_populates="post")
    
    # Many-to-Many: Post has many tags
    tags = ManyToMany("Tag", secondary=post_tag_association, back_populates="posts")

class Comment(Model):
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = StringField(max_length=500)
    created_at = DateTimeField(auto_now_add=True)
    
    # Many-to-One: Comment belongs to one user
    user_id: int = ForeignKeyField("users", nullable=False, on_delete="CASCADE")
    user = ManyToOne("User", back_populates="comments")
    
    # Many-to-One: Comment belongs to one post
    post_id: int = ForeignKeyField("posts", nullable=False, on_delete="CASCADE")
    post = ManyToOne("Post", back_populates="comments")

class Tag(Model):
    __tablename__ = "tags"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=50, unique=True)
    
    # Many-to-Many: Tag can be on many posts
    posts = ManyToMany("Post", secondary=post_tag_association, back_populates="tags")
```

## Next Steps

- Learn about [advanced querying](04-advanced-querying.md)
- Explore [composite keys](12-composite-keys.md)
- Discover [polymorphic models](14-polymorphic-models.md)

## Support

- **Developer**: Abdulaziz Al-Qadimi
- **Email**: eng7mi@gmail.com
- **Repository**: https://github.com/Alqudimi/FastApiOrm
