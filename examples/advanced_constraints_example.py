"""
Advanced Database Constraints Examples

Demonstrates CHECK constraints, unique together, foreign key helpers, and validation.
"""

import asyncio
from fastapi_orm import (
    Database,
    Model,
    IntegerField,
    StringField,
    FloatField,
    ForeignKeyField,
    ManyToOne,
)
from fastapi_orm.advanced_constraints import (
    ConstraintBuilder,
    CheckConstraintValidator,
    UniqueTogetherValidator,
    ForeignKeyHelper,
    create_constraint_set,
    enforce_constraints,
)


# Setup database
db = Database("sqlite+aiosqlite:///./constraints_demo.db", echo=True)


# Define models
class Company(Model):
    __tablename__ = "companies"
    
    id: int = IntegerField(primary_key=True)
    name: str = StringField(max_length=200, nullable=False)


class Product(Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    sku: str = StringField(max_length=50, nullable=False)
    name: str = StringField(max_length=200, nullable=False)
    price: float = FloatField(nullable=False)
    company_id: int = ForeignKeyField("companies", nullable=False)
    stock: int = IntegerField(default=0)
    
    company = ManyToOne("Company")
    
    # Define unique together constraint
    __unique_together__ = [
        ("sku", "company_id"),  # SKU must be unique per company
    ]


async def get_session():
    """Get database session."""
    async for session in db.get_session():
        yield session


async def example_1_check_constraints():
    """Example 1: Application-level CHECK constraints"""
    print("\n" + "="*50)
    print("Example 1: CHECK Constraint Validation")
    print("="*50)
    
    # Create validator
    validator = CheckConstraintValidator()
    validator.add_range("price", min_value=0, max_value=10000)
    validator.add_range("stock", min_value=0)
    validator.add_regex("sku", r'^[A-Z]{3}-\d{4}$', "SKU must be format: ABC-1234")
    
    async for session in get_session():
        print("\n✓ Valid product (should succeed):")
        try:
            data = {"sku": "ABC-1234", "price": 99.99, "stock": 100}
            await validator.validate(data)
            print(f"  Validated: {data}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print("\n✗ Invalid price (should fail):")
        try:
            data = {"sku": "ABC-1234", "price": -5.00, "stock": 100}
            await validator.validate(data)
            print(f"  Validated: {data}")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print("\n✗ Invalid SKU format (should fail):")
        try:
            data = {"sku": "invalid", "price": 99.99, "stock": 100}
            await validator.validate(data)
            print(f"  Validated: {data}")
        except Exception as e:
            print(f"  ✗ Error: {e}")


async def example_2_unique_together():
    """Example 2: Unique together validation"""
    print("\n" + "="*50)
    print("Example 2: Unique Together Validation")
    print("="*50)
    
    async for session in get_session():
        # Create a company
        company = await Company.create(session, name="Tech Corp")
        
        print(f"\n✓ Creating product with SKU 'TECH-001' for company {company.id}")
        product1 = await Product.create(
            session,
            sku="TECH-001",
            name="Widget",
            price=99.99,
            company_id=company.id,
            stock=50
        )
        print(f"  Created: {product1.name} (SKU: {product1.sku})")
        
        print(f"\n✗ Trying to create duplicate SKU for same company (should fail)")
        try:
            # First validate
            await UniqueTogetherValidator.validate(
                session,
                Product,
                {"sku": "TECH-001", "company_id": company.id}
            )
            print("  Validation passed (unexpected!)")
        except Exception as e:
            print(f"  ✗ Validation failed: {e}")
        
        # Create another company
        company2 = await Company.create(session, name="Other Corp")
        
        print(f"\n✓ Creating product with same SKU for different company {company2.id} (should succeed)")
        product2 = await Product.create(
            session,
            sku="TECH-001",
            name="Widget Clone",
            price=89.99,
            company_id=company2.id,
            stock=30
        )
        print(f"  Created: {product2.name} (SKU: {product2.sku})")


async def example_3_foreign_key_validation():
    """Example 3: Foreign key validation"""
    print("\n" + "="*50)
    print("Example 3: Foreign Key Validation")
    print("="*50)
    
    async for session in get_session():
        print("\n✓ Validating existing company (should succeed):")
        try:
            company = await Company.create(session, name="Valid Corp")
            await ForeignKeyHelper.validate_fk(session, Company, "id", company.id)
            print(f"  ✓ Company {company.id} exists")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print("\n✗ Validating non-existent company (should fail):")
        try:
            await ForeignKeyHelper.validate_fk(session, Company, "id", 99999)
            print("  ✓ Validation passed (unexpected!)")
        except Exception as e:
            print(f"  ✗ Error: {e}")


async def example_4_dependency_check():
    """Example 4: Check dependencies before delete"""
    print("\n" + "="*50)
    print("Example 4: Dependency Checking")
    print("="*50)
    
    async for session in get_session():
        # Create company and products
        company = await Company.create(session, name="Delete Test Corp")
        
        for i in range(3):
            await Product.create(
                session,
                sku=f"DEL-{i:04d}",
                name=f"Product {i}",
                price=99.99,
                company_id=company.id,
                stock=10
            )
        
        print(f"\n📊 Checking dependencies for company {company.id}")
        
        # Count dependent products
        count = await ForeignKeyHelper.get_dependent_count(
            session,
            Product,
            "company_id",
            company.id
        )
        print(f"  Found {count} dependent products")
        
        # Check if can delete
        can_delete, reasons = await ForeignKeyHelper.can_delete(
            session,
            Company,
            company.id,
            [(Product, "company_id")]
        )
        
        if can_delete:
            print("  ✓ Can safely delete company")
        else:
            print("  ✗ Cannot delete company:")
            for reason in reasons:
                print(f"    - {reason}")


async def example_5_constraint_builder():
    """Example 5: Building complex constraints"""
    print("\n" + "="*50)
    print("Example 5: Constraint Builder")
    print("="*50)
    
    # Create constraint builder
    builder = create_constraint_set(Product)
    
    # Add various constraints
    builder.add_check(
        "positive_price",
        "price > 0",
        deferrable=False
    )
    
    builder.add_check(
        "valid_stock",
        "stock >= 0",
        deferrable=False
    )
    
    builder.add_unique(
        ["sku", "company_id"],
        name="unique_sku_per_company"
    )
    
    print("\n📝 Defined constraints:")
    constraints = builder.get_constraints()
    for i, constraint in enumerate(constraints, 1):
        print(f"  {i}. {constraint}")
    
    print("\nNote: These constraints would be applied during table creation or migration")


async def example_6_custom_validators():
    """Example 6: Custom validation rules"""
    print("\n" + "="*50)
    print("Example 6: Custom Validation Rules")
    print("="*50)
    
    validator = CheckConstraintValidator()
    
    # Add custom validation rule
    def validate_discount(price):
        """Prices must be multiples of 0.99 for marketing purposes"""
        return (price * 100) % 99 == 0
    
    validator.add_rule(
        "price",
        validate_discount,
        "Price must be a multiple of 0.99 (e.g., 9.99, 19.99)"
    )
    
    async for session in get_session():
        print("\n✓ Testing valid price (9.99):")
        try:
            await validator.validate({"price": 9.99})
            print("  ✓ Validation passed")
        except Exception as e:
            print(f"  ✗ Error: {e}")
        
        print("\n✗ Testing invalid price (10.00):")
        try:
            await validator.validate({"price": 10.00})
            print("  ✓ Validation passed (unexpected!)")
        except Exception as e:
            print(f"  ✗ Error: {e}")


async def seed_data():
    """Seed the database with sample data"""
    async for session in get_session():
        print("Creating sample data...")


async def main():
    """Run all examples"""
    # Create tables
    await db.create_tables()
    
    # Seed data
    await seed_data()
    
    # Run examples
    await example_1_check_constraints()
    await example_2_unique_together()
    await example_3_foreign_key_validation()
    await example_4_dependency_check()
    await example_5_constraint_builder()
    await example_6_custom_validators()
    
    print("\n" + "="*50)
    print("All examples completed!")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
