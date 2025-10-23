"""
Advanced Query Builder Examples

Demonstrates CTEs, subqueries, window functions, and CASE statements.
"""

import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    DateTimeField,
    ForeignKeyField,
    ManyToOne,
    OneToMany,
)
from fastapi_orm.query_builder import (
    QueryBuilder,
    CaseBuilder,
    WindowFunction,
    SubqueryBuilder,
    build_case,
    cte,
)


# Setup database
db = Database("sqlite+aiosqlite:///./query_builder_demo.db", echo=True)


# Define models
class Department(Model):
    __tablename__ = "departments"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    
    employees = OneToMany("Employee", back_populates="department")


class Employee(Model):
    __tablename__ = "employees"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=100, nullable=False)
    department_id: int = ForeignKeyField("departments", nullable=False)
    salary: float = FloatField(nullable=False)
    hire_date = DateTimeField(auto_now_add=True)
    
    department = ManyToOne("Department", back_populates="employees")


async def get_session():
    """Get database session."""
    async for session in db.get_session():
        yield session


async def example_1_cte():
    """Example 1: Using Common Table Expressions (CTEs)"""
    print("\n" + "="*50)
    print("Example 1: Common Table Expressions (CTEs)")
    print("="*50)
    
    async for session in get_session():
        # Create a CTE for high earners
        qb = QueryBuilder(Employee)
        
        high_earners_cte = cte(
            select(Employee).where(Employee.salary > 75000),
            name="high_earners"
        )
        
        # Query from the CTE
        qb = QueryBuilder(Employee)
        qb.with_cte(high_earners_cte)
        qb.select_from_cte(high_earners_cte)
        
        results = await qb.execute(session)
        
        print(f"\nHigh earners (salary > 75000): {len(results)}")
        for emp in results:
            print(f"  - {emp.name}: ${emp.salary:,.2f}")


async def example_2_window_functions():
    """Example 2: Window Functions - Ranking employees"""
    print("\n" + "="*50)
    print("Example 2: Window Functions - Ranking")
    print("="*50)
    
    async for session in get_session():
        # Rank employees by salary within each department
        ranked = await WindowFunction.rank_over(
            session,
            Employee,
            partition_by=[Employee.department_id],
            order_by=[Employee.salary.desc()],
            dense=True
        )
        
        print("\nEmployees ranked by salary within department:")
        for emp, rank in ranked:
            dept = await Department.get(session, emp.department_id)
            print(f"  Rank {rank}: {emp.name} (${emp.salary:,.2f}) - {dept.name if dept else 'Unknown'}")


async def example_3_row_number():
    """Example 3: ROW_NUMBER for pagination"""
    print("\n" + "="*50)
    print("Example 3: ROW_NUMBER Window Function")
    print("="*50)
    
    async for session in get_session():
        # Add row numbers ordered by hire date
        numbered = await WindowFunction.row_number(
            session,
            Employee,
            order_by=[Employee.hire_date]
        )
        
        print("\nEmployees with row numbers (ordered by hire date):")
        for emp, row_num in numbered[:5]:  # Show first 5
            print(f"  {row_num}. {emp.name} - Hired: {emp.hire_date}")


async def example_4_ntile():
    """Example 4: NTILE - Divide into salary quartiles"""
    print("\n" + "="*50)
    print("Example 4: NTILE - Salary Quartiles")
    print("="*50)
    
    async for session in get_session():
        # Divide employees into 4 salary quartiles
        quartiles = await WindowFunction.ntile(
            session,
            Employee,
            n=4,
            order_by=[Employee.salary]
        )
        
        print("\nEmployees divided into 4 salary quartiles:")
        for emp, quartile in sorted(quartiles, key=lambda x: x[1]):
            print(f"  Q{quartile}: {emp.name} - ${emp.salary:,.2f}")


async def example_5_case_statements():
    """Example 5: CASE/WHEN statements"""
    print("\n" + "="*50)
    print("Example 5: CASE/WHEN Statements")
    print("="*50)
    
    async for session in get_session():
        # Create salary bands using CASE
        salary_band = build_case(
            (Employee.salary < 50000, "Entry Level"),
            (Employee.salary < 75000, "Mid Level"),
            (Employee.salary < 100000, "Senior Level"),
            else_="Executive"
        ).label("salary_band")
        
        query = select(Employee.name, Employee.salary, salary_band)
        result = await session.execute(query)
        
        print("\nEmployees with salary bands:")
        for name, salary, band in result.all():
            print(f"  {name}: ${salary:,.2f} - {band}")


async def example_6_subqueries():
    """Example 6: Subqueries"""
    print("\n" + "="*50)
    print("Example 6: Subqueries")
    print("="*50)
    
    async for session in get_session():
        # Find departments with average salary > $70,000 using subquery
        avg_salary_subq = (
            select(func.avg(Employee.salary))
            .where(Employee.department_id == Department.id)
            .correlate(Department)
            .scalar_subquery()
        )
        
        query = select(Department.name, avg_salary_subq.label("avg_salary")).where(
            avg_salary_subq > 70000
        )
        
        result = await session.execute(query)
        
        print("\nDepartments with average salary > $70,000:")
        for dept_name, avg_sal in result.all():
            print(f"  {dept_name}: Average ${avg_sal:,.2f}")


async def example_7_exists_subquery():
    """Example 7: EXISTS subquery"""
    print("\n" + "="*50)
    print("Example 7: EXISTS Subquery")
    print("="*50)
    
    async for session in get_session():
        # Find departments that have employees earning > $80,000
        high_earner_exists = SubqueryBuilder.exists(
            select(Employee.id)
            .where(Employee.department_id == Department.id)
            .where(Employee.salary > 80000)
        )
        
        query = select(Department).where(high_earner_exists)
        result = await session.execute(query)
        departments = result.scalars().all()
        
        print("\nDepartments with employees earning > $80,000:")
        for dept in departments:
            print(f"  {dept.name}")


async def example_8_union():
    """Example 8: UNION queries"""
    print("\n" + "="*50)
    print("Example 8: UNION Queries")
    print("="*50)
    
    async for session in get_session():
        # Get employees from two salary ranges
        high_earners = select(Employee).where(Employee.salary > 90000)
        low_earners = select(Employee).where(Employee.salary < 40000)
        
        qb = QueryBuilder(Employee)
        qb._query = high_earners.union(low_earners)
        
        results = await qb.execute(session)
        
        print(f"\nEmployees earning < $40k or > $90k: {len(results)}")
        for emp in results:
            print(f"  {emp.name}: ${emp.salary:,.2f}")


async def seed_data():
    """Seed the database with sample data"""
    async for session in get_session():
        # Create departments
        eng_dept = await Department.create(session, name="Engineering")
        sales_dept = await Department.create(session, name="Sales")
        hr_dept = await Department.create(session, name="HR")
        
        # Create employees
        employees = [
            ("Alice Johnson", eng_dept.id, 95000),
            ("Bob Smith", eng_dept.id, 82000),
            ("Carol Davis", eng_dept.id, 78000),
            ("David Brown", sales_dept.id, 65000),
            ("Eve Wilson", sales_dept.id, 72000),
            ("Frank Miller", sales_dept.id, 88000),
            ("Grace Lee", hr_dept.id, 58000),
            ("Henry Chen", hr_dept.id, 62000),
            ("Ivy Martinez", eng_dept.id, 105000),
            ("Jack Taylor", sales_dept.id, 45000),
        ]
        
        for name, dept_id, salary in employees:
            await Employee.create(session, name=name, department_id=dept_id, salary=salary)
        
        print("Sample data created successfully!")


async def main():
    """Run all examples"""
    # Create tables
    await db.create_tables()
    
    # Seed data
    await seed_data()
    
    # Run examples
    await example_1_cte()
    await example_2_window_functions()
    await example_3_row_number()
    await example_4_ntile()
    await example_5_case_statements()
    await example_6_subqueries()
    await example_7_exists_subquery()
    await example_8_union()
    
    print("\n" + "="*50)
    print("All examples completed!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
