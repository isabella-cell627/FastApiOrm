# Relationships

Relationship definitions for connecting models. All relationship types are imported from `fastapi_orm`.

## Foreign Key Fields

### ForeignKeyField

```python
ForeignKeyField(
    to: str,
    nullable: bool = True,
    on_delete: str = "CASCADE",
    on_update: str = "CASCADE"
) -> Field
```

Creates a foreign key reference to another table.

**Parameters:**
- `to` (str): Target table name
- `nullable` (bool): Allow NULL. Default: True
- `on_delete` (str): Action on delete. Options: `"CASCADE"`, `"SET NULL"`, `"RESTRICT"`, `"NO ACTION"`. Default: `"CASCADE"`
- `on_update` (str): Action on update. Default: `"CASCADE"`

**Returns:** Field instance

**Example:**
```python
from fastapi_orm import Model, IntegerField, StringField, ForeignKeyField

class User(Model):
    __tablename__ = "users"
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    author_id: int = ForeignKeyField("users", nullable=False)
```

## Relationship Types

### OneToMany

```python
OneToMany(
    to: str,
    back_populates: str,
    lazy: str = "select"
) -> RelationshipProperty
```

Defines one-to-many relationship (parent side).

**Parameters:**
- `to` (str): Related model class name
- `back_populates` (str): Name of reverse relationship on related model
- `lazy` (str): Loading strategy. Options: `"select"`, `"selectin"`, `"joined"`, `"subquery"`. Default: `"select"`

**Returns:** SQLAlchemy RelationshipProperty

**Example:**
```python
from fastapi_orm import OneToMany, ManyToOne

class User(Model):
    __tablename__ = "users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100)
    
    posts = OneToMany("Post", back_populates="author")

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    author_id: int = ForeignKeyField("users")
    
    author = ManyToOne("User", back_populates="posts")
```

**Usage:**
```python
user = await User.get(session, 1)

for post in user.posts:
    print(post.title)
```

### ManyToOne

```python
ManyToOne(
    to: str,
    back_populates: str,
    lazy: str = "select"
) -> RelationshipProperty
```

Defines many-to-one relationship (child side).

**Parameters:**
- `to` (str): Related model class name
- `back_populates` (str): Name of reverse relationship on parent model
- `lazy` (str): Loading strategy. Default: `"select"`

**Returns:** SQLAlchemy RelationshipProperty

**Example:**
```python
class Comment(Model):
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = TextField()
    post_id: int = ForeignKeyField("posts", nullable=False)
    
    post = ManyToOne("Post", back_populates="comments")

class Post(Model):
    __tablename__ = "posts"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    
    comments = OneToMany("Comment", back_populates="post")
```

**Usage:**
```python
comment = await Comment.get(session, 1)
post = comment.post
print(f"Comment on: {post.title}")
```

### ManyToMany

```python
ManyToMany(
    to: str,
    secondary: Table,
    back_populates: str,
    lazy: str = "select"
) -> RelationshipProperty
```

Defines many-to-many relationship.

**Parameters:**
- `to` (str): Related model class name
- `secondary` (Table): Association table
- `back_populates` (str): Name of reverse relationship
- `lazy` (str): Loading strategy. Default: `"select"`

**Returns:** SQLAlchemy RelationshipProperty

**Example:**
```python
from fastapi_orm import ManyToMany, create_association_table, Base

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
    
    tags = ManyToMany(
        "Tag",
        secondary=post_tag_association,
        back_populates="posts"
    )

class Tag(Model):
    __tablename__ = "tags"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=50, unique=True)
    
    posts = ManyToMany(
        "Post",
        secondary=post_tag_association,
        back_populates="tags"
    )
```

**Usage:**
```python
post = await Post.get(session, 1)

for tag in post.tags:
    print(tag.name)

tag = await Tag.get(session, 1)

post.tags.append(tag)
await session.commit()
```

## Association Tables

### create_association_table()

```python
create_association_table(
    table_name: str,
    left_table: str,
    right_table: str,
    base: DeclarativeMeta,
    left_column_name: Optional[str] = None,
    right_column_name: Optional[str] = None
) -> Table
```

Creates an association table for many-to-many relationships.

**Parameters:**
- `table_name` (str): Name of association table
- `left_table` (str): Left side table name
- `right_table` (str): Right side table name
- `base` (DeclarativeMeta): SQLAlchemy Base class
- `left_column_name` (str, optional): Custom left column name
- `right_column_name` (str, optional): Custom right column name

**Returns:** SQLAlchemy Table

**Example:**
```python
from fastapi_orm import Base, create_association_table

student_course = create_association_table(
    "student_courses",
    "students",
    "courses",
    Base
)

class Student(Model):
    __tablename__ = "students"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    
    courses = ManyToMany(
        "Course",
        secondary=student_course,
        back_populates="students"
    )

class Course(Model):
    __tablename__ = "courses"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200)
    
    students = ManyToMany(
        "Student",
        secondary=student_course,
        back_populates="courses"
    )
```

## Loading Strategies

### Select (Default)

Loads related objects in separate queries.

```python
posts = OneToMany("Post", back_populates="author", lazy="select")
```

### SelectIn

Loads related objects in a single additional query (efficient for collections).

```python
posts = OneToMany("Post", back_populates="author", lazy="selectin")
```

### Joined

Loads related objects in the same query using JOIN (efficient for single objects).

```python
author = ManyToOne("User", back_populates="posts", lazy="joined")
```

### Subquery

Loads related objects using a subquery.

```python
posts = OneToMany("Post", back_populates="author", lazy="subquery")
```

## Eager Loading

Use `selectinload`, `joinedload`, or `subqueryload` for explicit eager loading:

```python
from sqlalchemy.orm import selectinload

users = await session.execute(
    select(User).options(selectinload(User.posts))
)
users = users.scalars().all()

for user in users:
    for post in user.posts:
        print(post.title)
```

## Cascading

### CASCADE

Delete/update children when parent is deleted/updated:

```python
author_id: int = ForeignKeyField("users", on_delete="CASCADE")
```

### SET NULL

Set foreign key to NULL when parent is deleted:

```python
author_id: int = ForeignKeyField("users", on_delete="SET NULL", nullable=True)
```

### RESTRICT

Prevent deletion if children exist:

```python
author_id: int = ForeignKeyField("users", on_delete="RESTRICT")
```

## Working with Relationships

### Adding Related Objects

```python
post = await Post.get(session, 1)
tag = await Tag.get(session, 1)

post.tags.append(tag)
await session.commit()
```

### Removing Related Objects

```python
post.tags.remove(tag)
await session.commit()
```

### Clearing All Related Objects

```python
post.tags.clear()
await session.commit()
```

### Accessing Related Objects

```python
user = await User.get(session, 1)
post_count = len(user.posts)

post = await Post.get(session, 1)
author_name = post.author.username
```

## Self-Referential Relationships

```python
class Category(Model):
    __tablename__ = "categories"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100)
    parent_id: int = ForeignKeyField(
        "categories",
        nullable=True,
        on_delete="CASCADE"
    )
    
    children = OneToMany(
        "Category",
        back_populates="parent",
        foreign_keys="Category.parent_id"
    )
    parent = ManyToOne(
        "Category",
        back_populates="children",
        foreign_keys="Category.parent_id"
    )
```

## Best Practices

1. **Use Descriptive Names:** Name relationships clearly (e.g., `author`, not `user`)
2. **Always Use back_populates:** Ensure bidirectional relationships are properly linked
3. **Choose Appropriate Loading:** Use `selectinload` for collections, `joined` for single objects
4. **Handle Cascades Carefully:** Consider data integrity when setting cascade options
5. **Avoid Circular Imports:** Use string references for model names

## See Also

- [Models](models.md) - Model class documentation
- [Fields](fields.md) - Field type reference
- [Queries](queries.md) - Querying relationships

---

*API Reference - Relationships*  
*FastAPI ORM v0.11.0*  
*Copyright © 2025 Abdulaziz Al-Qadimi*
