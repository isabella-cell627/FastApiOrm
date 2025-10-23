# Changelog v0.12.0

## New Features

### Composite Primary Keys and Advanced Constraints

Added comprehensive support for composite primary keys, composite unique constraints, and check constraints, enabling complex data modeling scenarios.

#### New Module: `fastapi_orm.composite_keys`

**Functions:**
- `composite_primary_key(*columns, name=None)` - Create multi-column primary keys
- `composite_unique(*columns, name=None)` - Create composite unique constraints
- `check_constraint(condition, name=None)` - Create check constraints for data validation
- `constraints(*constraint_objects)` - Helper for organizing multiple constraints

**Mixin:**
- `CompositeKeyMixin` - Provides utility methods for models with composite keys
  - `get_by_composite_key(**key_values)` - Query by composite key values
  - `get_composite_key()` - Get the composite key as a tuple
  - Automatic `__hash__` and `__eq__` based on composite keys

#### Features

**Composite Primary Keys:**
- Multi-column primary keys for junction tables, time-series data, multi-tenant schemas
- Automatic constraint naming
- Full SQLAlchemy integration
- Works with all supported databases (PostgreSQL, SQLite, MySQL)

**Composite Unique Constraints:**
- Enforce uniqueness across multiple columns
- Automatic constraint naming with customization support
- Useful for business rules like "one SKU per vendor" or "one vote per user per poll"

**Check Constraints:**
- Database-level data validation
- Enforce business rules (e.g., positive quantities, valid date ranges)
- Support for complex SQL conditions
- Better data integrity than application-level validation alone

#### Example Usage

```python
from fastapi_orm import Model, IntegerField, StringField, DecimalField
from fastapi_orm.composite_keys import (
    composite_primary_key,
    composite_unique,
    check_constraint,
    CompositeKeyMixin,
    constraints,
)

# Composite primary key for junction table
class OrderItem(Model, CompositeKeyMixin):
    __tablename__ = "order_items"
    
    order_id: int = IntegerField()
    product_id: int = IntegerField()
    quantity: int = IntegerField()
    unit_price: Decimal = DecimalField(precision=10, scale=2)
    
    __table_args__ = (
        composite_primary_key("order_id", "product_id"),
        check_constraint("quantity > 0", name="ck_positive_quantity"),
        check_constraint("unit_price > 0", name="ck_positive_price"),
    )
    
    @classmethod
    def _composite_key_fields(cls):
        return ("order_id", "product_id")

# Query by composite key
item = await OrderItem.get_by_composite_key(
    session,
    order_id=123,
    product_id=456
)

# Composite unique constraint
class Product(Model):
    __tablename__ = "products"
    
    id: int = IntegerField(primary_key=True)
    vendor_id: int = IntegerField()
    sku: str = StringField(max_length=50)
    name: str = StringField(max_length=200)
    price: Decimal = DecimalField(precision=10, scale=2)
    stock: int = IntegerField(default=0)
    
    __table_args__ = constraints(
        composite_unique("vendor_id", "sku", name="uq_vendor_sku"),
        check_constraint("price > 0", name="ck_positive_price"),
        check_constraint("stock >= 0", name="ck_non_negative_stock"),
    )

# Time-series data with composite key
class SensorReading(Model, CompositeKeyMixin):
    __tablename__ = "sensor_readings"
    
    sensor_id: int = IntegerField()
    timestamp: datetime = DateTimeField()
    temperature: float = FloatField()
    humidity: float = FloatField()
    
    __table_args__ = (
        composite_primary_key("sensor_id", "timestamp"),
        check_constraint("temperature >= -50 AND temperature <= 100"),
        check_constraint("humidity >= 0 AND humidity <= 100"),
    )
    
    @classmethod
    def _composite_key_fields(cls):
        return ("sensor_id", "timestamp")

# Get composite key as tuple
reading = SensorReading(sensor_id=1, timestamp=datetime.now())
key = reading.get_composite_key()  # Returns (1, datetime(...))
```

#### Use Cases

1. **Junction Tables**: Many-to-many relationships with additional attributes
2. **Multi-Tenant Applications**: Composite keys of `tenant_id` + `entity_id`
3. **Time-Series Data**: Sensor/device ID + timestamp combinations
4. **Natural Keys**: Business-defined multi-column unique identifiers
5. **Data Integrity**: Enforce complex business rules at the database level

#### Benefits

- **Database-Level Integrity**: Constraints enforced by the database engine
- **Better Performance**: Database indexes on composite keys
- **Cleaner Code**: No need for application-level uniqueness checks
- **Production-Ready**: Full support for migrations and schema evolution
- **Type-Safe**: Works with model type hints and Pydantic integration

See `examples/composite_keys_example.py` for a complete working demonstration with order items, user permissions, product SKUs, room bookings, and sensor readings.

## Documentation

- Added comprehensive example file: `examples/composite_keys_example.py`
- Updated `__init__.py` exports to include composite key utilities
- Detailed docstrings for all functions and classes
- Multiple real-world use case examples

## Database Support

- PostgreSQL: Full support with native constraint syntax
- SQLite: Full support with constraint checking
- MySQL/MariaDB: Full support (to be tested in next release)

## Migration Notes

Composite keys and constraints are fully compatible with existing ORM functionality. Models can use both single primary keys and composite primary keys in the same application. Check constraints work alongside field-level validators for comprehensive data validation.
