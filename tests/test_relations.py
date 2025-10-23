import pytest
import pytest_asyncio
from fastapi_orm import (
    Database,
    IntegerField,
    StringField,
    TextField,
)
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.relations import (
    ForeignKeyField,
    OneToMany,
    ManyToOne,
    ManyToMany,
    create_association_table,
)


class Author(TestModel):
    __tablename__ = "rel_authors"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    
    books = OneToMany("Book", back_populates="author")


class Book(TestModel):
    __tablename__ = "rel_books"
    
    id: int = IntegerField(primary_key=True)
    title: str = StringField(max_length=200, nullable=False)
    author_id: int = ForeignKeyField("rel_authors", nullable=False)
    
    author = ManyToOne("Author", back_populates="books")
    tags = ManyToMany("Tag", secondary="book_tags", back_populates="books")


book_tags = create_association_table("book_tags", "rel_books", "rel_tags", TestBase)


class Tag(TestModel):
    __tablename__ = "rel_tags"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=50, nullable=False, unique=True)
    
    books = ManyToMany("Book", secondary="book_tags", back_populates="tags")


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_one_to_many_relationship(db):
    """Test OneToMany relationship"""
    async with db.session() as session:
        author = await Author.create(session, name="John Doe")
        
        book1 = await Book.create(
            session,
            title="Book 1",
            author_id=author.id
        )
        book2 = await Book.create(
            session,
            title="Book 2",
            author_id=author.id
        )
        
        retrieved_author = await Author.get(session, author.id)
        assert len(retrieved_author.books) == 2
        book_titles = {b.title for b in retrieved_author.books}
        assert book_titles == {"Book 1", "Book 2"}


@pytest.mark.asyncio
async def test_many_to_one_relationship(db):
    """Test ManyToOne relationship"""
    async with db.session() as session:
        author = await Author.create(session, name="Jane Doe")
        
        book = await Book.create(
            session,
            title="My Book",
            author_id=author.id
        )
        
        retrieved_book = await Book.get(session, book.id)
        assert retrieved_book.author.name == "Jane Doe"
        assert retrieved_book.author.id == author.id


@pytest.mark.asyncio
async def test_foreign_key_constraint(db):
    """Test foreign key field creation"""
    async with db.session() as session:
        author = await Author.create(session, name="Test Author")
        
        book = await Book.create(
            session,
            title="Test Book",
            author_id=author.id
        )
        
        assert book.author_id == author.id


@pytest.mark.asyncio
async def test_many_to_many_relationship(db):
    """Test ManyToMany relationship"""
    async with db.session() as session:
        tag1 = await Tag.create(session, name="Fiction")
        tag2 = await Tag.create(session, name="Adventure")
        
        author = await Author.create(session, name="Author")
        book = await Book.create(
            session,
            title="Tagged Book",
            author_id=author.id
        )
        
        book.tags.append(tag1)
        book.tags.append(tag2)
        await session.commit()
        
        retrieved_book = await Book.get(session, book.id)
        assert len(retrieved_book.tags) == 2
        tag_names = {t.name for t in retrieved_book.tags}
        assert tag_names == {"Fiction", "Adventure"}


@pytest.mark.asyncio
async def test_many_to_many_reverse(db):
    """Test ManyToMany relationship from reverse side"""
    async with db.session() as session:
        tag = await Tag.create(session, name="Science")
        
        author = await Author.create(session, name="Author")
        
        book1 = await Book.create(session, title="Book 1", author_id=author.id)
        book2 = await Book.create(session, title="Book 2", author_id=author.id)
        
        tag.books.append(book1)
        tag.books.append(book2)
        await session.commit()
        
        retrieved_tag = await Tag.get(session, tag.id)
        assert len(retrieved_tag.books) == 2
        book_titles = {b.title for b in retrieved_tag.books}
        assert book_titles == {"Book 1", "Book 2"}


@pytest.mark.asyncio
async def test_cascade_delete(db):
    """Test cascade delete on OneToMany relationship"""
    async with db.session() as session:
        author = await Author.create(session, name="Cascade Author")
        
        book1 = await Book.create(session, title="Book 1", author_id=author.id)
        book2 = await Book.create(session, title="Book 2", author_id=author.id)
        
        await author.delete(session)
        
        remaining_books = await Book.filter_by(session)
        assert len(remaining_books) == 0


@pytest.mark.asyncio
async def test_association_table_creation(db):
    """Test association table helper creates valid table"""
    assert book_tags is not None
    assert "book_tags" in str(book_tags)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
