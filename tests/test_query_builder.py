import pytest
import pytest_asyncio
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    BooleanField,
)
from fastapi_orm.query_builder import QueryBuilder, CaseBuilder, WindowFunction
from sqlalchemy import func


class Employee(Model):
    __tablename__ = "test_employees"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    department: str = StringField(max_length=50, nullable=False)
    salary: float = FloatField(nullable=False)
    is_active: bool = BooleanField(default=True)


@pytest_asyncio.fixture
async def db():
    database = Database("sqlite+aiosqlite:///:memory:", echo=False)
    await database.create_tables()
    yield database
    await database.close()


@pytest_asyncio.fixture
async def sample_employees(db):
    async with db.session() as session:
        employees = await Employee.bulk_create(session, [
            {"name": "Alice", "department": "Engineering", "salary": 100000},
            {"name": "Bob", "department": "Engineering", "salary": 90000},
            {"name": "Charlie", "department": "Sales", "salary": 80000},
            {"name": "Diana", "department": "Sales", "salary": 85000},
            {"name": "Eve", "department": "HR", "salary": 70000},
        ])
    return employees


@pytest.mark.asyncio
async def test_query_builder_basic(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        results = await qb.where(Employee.department == "Engineering").all(session)
        assert len(results) == 2
        names = {e.name for e in results}
        assert names == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_query_builder_order_by(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        results = await qb.order_by(Employee.salary.desc()).all(session)
        assert len(results) == 5
        assert results[0].name == "Alice"
        assert results[4].name == "Eve"


@pytest.mark.asyncio
async def test_query_builder_limit_offset(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        results = await qb.order_by(Employee.name).limit(2).offset(1).all(session)
        assert len(results) == 2
        assert results[0].name == "Bob"


@pytest.mark.asyncio
async def test_query_builder_group_by(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        results = await qb.select(
            Employee.department,
            func.count(Employee.id).label("count")
        ).group_by(Employee.department).all(session)
        
        assert len(results) == 3
        dept_counts = {r.department: r.count for r in results}
        assert dept_counts["Engineering"] == 2
        assert dept_counts["Sales"] == 2
        assert dept_counts["HR"] == 1


@pytest.mark.asyncio
async def test_query_builder_having(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        results = await qb.select(
            Employee.department,
            func.count(Employee.id).label("count")
        ).group_by(
            Employee.department
        ).having(
            func.count(Employee.id) > 1
        ).all(session)
        
        assert len(results) == 2


@pytest.mark.asyncio
async def test_query_builder_count(db, sample_employees):
    qb = QueryBuilder(Employee)
    async with db.session() as session:
        count = await qb.where(Employee.department == "Engineering").count(session)
        assert count == 2


@pytest.mark.asyncio
async def test_case_builder(db, sample_employees):
    async with db.session() as session:
        case_stmt = CaseBuilder().when(
            Employee.salary > 90000, "High"
        ).when(
            Employee.salary > 75000, "Medium"
        ).else_("Low").build()
        
        qb = QueryBuilder(Employee)
        results = await qb.select(
            Employee.name,
            case_stmt.label("salary_tier")
        ).all(session)
        
        assert len(results) == 5
        tiers = {r.name: r.salary_tier for r in results}
        assert tiers["Alice"] == "High"
        assert tiers["Charlie"] == "Medium"
        assert tiers["Eve"] == "Low"


@pytest.mark.asyncio
async def test_query_builder_distinct(db):
    async with db.session() as session:
        await Employee.bulk_create(session, [
            {"name": "John", "department": "IT", "salary": 50000},
            {"name": "Jane", "department": "IT", "salary": 55000},
            {"name": "Jack", "department": "HR", "salary": 60000},
        ])
        
        qb = QueryBuilder(Employee)
        results = await qb.select(Employee.department).distinct().all(session)
        
        departments = {r.department for r in results}
        assert "IT" in departments
        assert "HR" in departments


@pytest.mark.asyncio
async def test_query_builder_union(db):
    async with db.session() as session:
        await Employee.bulk_create(session, [
            {"name": "Alice", "department": "Engineering", "salary": 100000},
            {"name": "Bob", "department": "Sales", "salary": 80000},
        ])
        
        qb1 = QueryBuilder(Employee)
        qb2 = QueryBuilder(Employee)
        
        query1 = qb1.select().where(Employee.department == "Engineering")
        query2 = qb2.select().where(Employee.salary > 75000)
        
        union_query = qb1.union(query2._query)
        results = await union_query.all(session)
        
        assert len(results) >= 1


@pytest.mark.asyncio
async def test_subquery(db, sample_employees):
    async with db.session() as session:
        qb = QueryBuilder(Employee)
        
        avg_salary_subquery = qb.select(
            func.avg(Employee.salary)
        ).subquery()
        
        results = await QueryBuilder(Employee).select().where(
            Employee.salary > avg_salary_subquery.c.anon_1
        ).all(session)
        
        assert len(results) >= 2
