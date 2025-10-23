import pytest
import pytest_asyncio
from fastapi_orm import Database, IntegerField, StringField
from fastapi_orm.testing import create_test_model_base

TestBase, TestModel = create_test_model_base()
from fastapi_orm.streaming import (
    QueryStreamer,
    CursorPaginator,
    BatchProcessor,
    stream_with_transform,
    stream_with_filter
)


class StreamUser(TestModel):
    __tablename__ = "test_stream_users"
    
    id: int = IntegerField(primary_key=True)
    username: str = StringField(max_length=100, nullable=False)
    email: str = StringField(max_length=255, nullable=False)
    score: int = IntegerField(default=0)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False, base=TestBase)
    await database.create_tables()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def sample_users(db):
    async with db.session() as session:
        users = []
        for i in range(50):
            user = await StreamUser.create(
                session,
                username=f"user{i}",
                email=f"user{i}@example.com",
                score=i
            )
            users.append(user)
        return users


@pytest.mark.asyncio
async def test_query_streamer_basic(db, sample_users):
    async with db.session() as session:
        streamer = QueryStreamer(StreamUser, chunk_size=10)
        
        collected = []
        async for chunk in streamer.stream(session):
            collected.extend(chunk)
        
        assert len(collected) == 50


@pytest.mark.asyncio
async def test_query_streamer_with_filter(db, sample_users):
    async with db.session() as session:
        streamer = QueryStreamer(
            StreamUser,
            chunk_size=10,
            filters={"score": {"gte": 25}}
        )
        
        collected = []
        async for chunk in streamer.stream(session):
            collected.extend(chunk)
        
        assert len(collected) == 25
        assert all(user.score >= 25 for user in collected)


@pytest.mark.asyncio
async def test_cursor_paginator_basic(db, sample_users):
    async with db.session() as session:
        paginator = CursorPaginator(StreamUser, page_size=10)
        
        page1 = await paginator.get_page(session, cursor=None)
        
        assert len(page1["items"]) == 10
        assert page1["has_next"] is True
        assert page1["next_cursor"] is not None


@pytest.mark.asyncio
async def test_cursor_paginator_navigation(db, sample_users):
    async with db.session() as session:
        paginator = CursorPaginator(StreamUser, page_size=10)
        
        page1 = await paginator.get_page(session, cursor=None)
        page2 = await paginator.get_page(session, cursor=page1["next_cursor"])
        
        assert len(page2["items"]) == 10
        assert page2["items"][0].id != page1["items"][0].id


@pytest.mark.asyncio
async def test_batch_processor(db, sample_users):
    async with db.session() as session:
        processor = BatchProcessor(batch_size=10)
        
        async def process_batch(batch):
            return [user.username for user in batch]
        
        results = await processor.process(
            session,
            StreamUser,
            process_batch
        )
        
        assert len(results) == 5
        assert len(results[0]) == 10


@pytest.mark.asyncio
async def test_stream_with_transform(db, sample_users):
    async with db.session() as session:
        
        def transform(user):
            return {"id": user.id, "name": user.username.upper()}
        
        streamer = stream_with_transform(
            StreamUser,
            transform,
            chunk_size=10
        )
        
        collected = []
        async for chunk in streamer.stream(session):
            collected.extend(chunk)
        
        assert len(collected) == 50
        assert all(isinstance(item, dict) for item in collected)
        assert all(item["name"].isupper() for item in collected)


@pytest.mark.asyncio
async def test_stream_with_filter_function(db, sample_users):
    async with db.session() as session:
        
        def filter_func(user):
            return user.score % 2 == 0
        
        streamer = stream_with_filter(
            StreamUser,
            filter_func,
            chunk_size=10
        )
        
        collected = []
        async for chunk in streamer.stream(session):
            collected.extend(chunk)
        
        assert all(user.score % 2 == 0 for user in collected)


@pytest.mark.asyncio
async def test_query_streamer_ordering(db, sample_users):
    async with db.session() as session:
        streamer = QueryStreamer(
            StreamUser,
            chunk_size=10,
            order_by="-score"
        )
        
        collected = []
        async for chunk in streamer.stream(session):
            collected.extend(chunk)
        
        assert collected[0].score > collected[-1].score


@pytest.mark.asyncio
async def test_batch_processor_with_updates(db, sample_users):
    async with db.session() as session:
        processor = BatchProcessor(batch_size=10)
        
        async def update_scores(batch):
            for user in batch:
                user.score += 10
            return batch
        
        await processor.process(session, StreamUser, update_scores)
        await session.commit()
    
    async with db.session() as session:
        users = await StreamUser.filter_by(session, id=sample_users[0].id)
        assert users[0].score == 10
