# FastAPI ORM v0.8.0 Changelog

## Release Date: October 2025

Version 0.8.0 is a major feature release that adds powerful development tools, testing utilities, advanced validation, database scaling capabilities, and polymorphic relationships.

---

## 🎯 New Features

### 1. CLI Tools & Code Generation

**Command-Line Interface** for rapid development and automation:

- **Database Inspection**: Examine database schema and structure
  ```bash
  python -m fastapi_orm inspect --database-url "sqlite:///./app.db"
  ```

- **Model Generation**: Auto-generate models from existing databases (reverse engineering)
  ```bash
  python -m fastapi_orm generate-models --database-url "postgresql://user:pass@localhost/db" --output models.py
  ```

- **CRUD Scaffolding**: Generate complete REST API endpoints from model definitions
  ```bash
  python -m fastapi_orm scaffold User --fields "name:str,email:str,age:int" --output api/users.py
  ```

- **Migration Management**: Simplified migration commands
  ```bash
  python -m fastapi_orm create-migration "Add users table"
  python -m fastapi_orm upgrade
  ```

**Key Benefits:**
- Reverse engineer existing databases instantly
- Generate boilerplate code automatically
- Scaffold complete CRUD APIs in seconds
- Streamline migration workflow

---

### 2. Model Factory System

**Test Data Generation** with realistic fake data:

```python
from fastapi_orm import ModelFactory, Faker, Sequence, SubFactory

class UserFactory(ModelFactory):
    class Meta:
        model = User
    
    username = Faker('user_name')
    email = Faker('email')
    age = Faker('random_int', min=18, max=80)
    is_active = True

# Generate test data
user = await UserFactory.create(session)
users = await UserFactory.create_batch(session, 10)

# With overrides
admin = await UserFactory.create(session, username="admin", is_active=True)
```

**Built-in Faker Providers:**
- Personal: `first_name`, `last_name`, `full_name`, `email`, `phone`, `address`
- Business: `company`, `job`, `domain`
- Internet: `url`, `ipv4`, `mac_address`, `user_agent`
- Text: `word`, `sentence`, `paragraph`, `text`, `slug`
- Numbers: `random_int`, `random_float`, `decimal`
- Dates: `date`, `datetime`, `time`, `future_date`, `past_date`
- Finance: `credit_card`, `currency_code`, `price`
- Misc: `uuid`, `boolean`, `color`, `file_name`

**Advanced Features:**
- `Sequence`: Sequential values with custom formatting
- `LazyAttribute`: Compute values based on other attributes
- `SubFactory`: Create related objects automatically
- Batch creation with common attributes

---

### 3. Advanced Validation System

**Comprehensive Field Validation** with built-in and custom validators:

```python
from fastapi_orm import Model, StringField, IntegerField
from fastapi_orm import (
    email_validator, length_range, min_value,
    strong_password, cross_field_validator
)

class User(Model):
    __tablename__ = "users"
    
    email: str = StringField(
        max_length=255,
        validators=[email_validator()]
    )
    
    age: int = IntegerField(
        validators=[min_value(18), max_value(120)]
    )
    
    password: str = StringField(
        max_length=255,
        validators=[
            length_range(8, 128),
            strong_password(min_length=8)
        ]
    )

# Cross-field validation
@cross_field_validator('end_date', 'start_date')
def validate_date_range(end_date, start_date):
    if end_date < start_date:
        raise ValidationError("End date must be after start date")
```

**Built-in Validators:**
- **Text**: `min_length`, `max_length`, `length_range`, `regex_validator`
- **Email & Web**: `email_validator`, `url_validator`, `ip_address_validator`
- **Phone & Finance**: `phone_validator`, `credit_card_validator` (Luhn algorithm)
- **Numbers**: `min_value`, `max_value`, `value_range`
- **Dates**: `date_range_validator`
- **Security**: `strong_password` (configurable requirements)
- **Data**: `choice_validator` (enum-like validation)
- **Async**: `unique_validator` (database uniqueness check)
- **Conditional**: `validate_if` (conditional validation)

**Cross-Field Validation:**
Compare and validate relationships between multiple fields

---

### 4. Read Replica Support

**Database Scaling** with automatic read/write splitting:

```python
from fastapi_orm import Database
from fastapi_orm import create_replica_manager

# Configure primary and replicas
manager = create_replica_manager(
    primary_url="postgresql+asyncpg://user:pass@primary:5432/db",
    replica_urls=[
        "postgresql+asyncpg://user:pass@replica1:5432/db",
        "postgresql+asyncpg://user:pass@replica2:5432/db",
    ],
    strategy="round_robin",  # or "random", "least_connections", "weighted"
    health_check_interval=30
)

await manager.connect()

# Read operations use replicas automatically
async with with_read_session(manager) as session:
    users = await User.all(session)  # Uses replica

# Write operations use primary
async with with_write_session(manager) as session:
    user = await User.create(session, username="john")  # Uses primary
```

**Load Balancing Strategies:**
- **Round Robin**: Distribute requests evenly across replicas
- **Random**: Random selection for simple load distribution
- **Least Connections**: Route to replica with fewest active connections
- **Weighted**: Distribute based on replica weights

**Features:**
- Automatic health checking and monitoring
- Failover to primary if replicas unavailable
- Connection pool management per replica
- Real-time statistics and metrics
- Replica status tracking

**Get Statistics:**
```python
stats = manager.get_stats()
# Returns: total/healthy replicas, active connections, query counts, response times
```

---

### 5. Polymorphic Relationships

**Flexible Model Associations** - models can relate to multiple types:

```python
from fastapi_orm import Model, PolymorphicMixin, GenericForeignKey

# Comments can belong to Posts, Photos, or any other model
class Comment(Model, PolymorphicMixin):
    __tablename__ = "comments"
    
    id: int = IntegerField(primary_key=True)
    content: str = StringField(max_length=500)
    
    # Polymorphic fields
    content_type: str = StringField(max_length=50)
    content_id: int = IntegerField()
    
    # Generic relationship
    content_object = GenericForeignKey('content_type', 'content_id')

# Usage
post = await Post.get(session, 1)
comment = await Comment.create(
    session,
    content="Great post!",
    content_object=post
)

# Access polymorphic relationship
related_object = await comment.get_content_object(session)
```

**Inheritance Patterns:**

- **Single Table Inheritance (STI)**: All subclasses share one table with a discriminator
- **Joined Table Inheritance (JTI)**: Each subclass has its own table joined to base
- **Concrete Table Inheritance (CTI)**: Each subclass is completely independent

**Features:**
- Generic foreign keys (like Django's ContentType)
- Content type registry for model lookup
- Polymorphic query helpers
- Collection management for polymorphic relations

---

### 6. Enhanced Migration Tools

**Advanced Migration Capabilities** for safe database changes:

```python
from fastapi_orm import (
    DataMigration, MigrationValidator,
    SafeMigrator, ZeroDowntimeMigration
)

# Data migration helper
async def migrate_user_data(session):
    migration = DataMigration(session, User)
    
    # Transform all emails to lowercase
    await migration.transform(
        lambda user: {'email': user.email.lower()},
        batch_size=100
    )
    
    # Copy column data
    await migration.copy_column('old_name', 'new_name')
    
    # Bulk update with mapping
    await migration.bulk_update_with_mapping(
        'status',
        {'active': 'enabled', 'inactive': 'disabled'}
    )

# Validate migration before running
validator = MigrationValidator()
issues = await validator.check_migration(session, '0001_add_users.py')

# Detect conflicts
conflicts = validator.detect_conflicts(migration_files)

# Safe migration with rollback
migrator = SafeMigrator(database_url)
success = await migrator.upgrade_with_rollback(session, validate=True)

# Zero-downtime operations
await ZeroDowntimeMigration.add_column_with_default(
    session, 'users', 'status', 'VARCHAR(20)', 'active'
)

await ZeroDowntimeMigration.rename_column_safe(
    session, 'users', 'old_name', 'new_name', 'VARCHAR(100)'
)
```

**Features:**
- **Data Migration Helpers**: Transform existing data during migrations
- **Conflict Detection**: Identify parallel migration conflicts
- **Safety Checks**: Validate migrations before execution
- **Automatic Rollback**: Revert on errors
- **Dependency Management**: Track migration dependencies
- **Zero-Downtime Strategies**: Migrate without service interruption

---

## 📚 Complete Feature List

### Development Tools
- ✅ CLI for database inspection and model generation
- ✅ CRUD endpoint scaffolding
- ✅ Reverse engineering from existing databases
- ✅ Migration management commands

### Testing & Data
- ✅ Model factories with realistic fake data
- ✅ 40+ built-in Faker providers
- ✅ Sequences and lazy attributes
- ✅ Sub-factories for related objects
- ✅ Batch creation utilities

### Validation
- ✅ 15+ built-in validators
- ✅ Email, URL, phone, credit card validation
- ✅ Password strength validation
- ✅ Cross-field validation
- ✅ Async validators (database checks)
- ✅ Custom validation functions
- ✅ Conditional validation

### Database Scaling
- ✅ Read replica support
- ✅ 4 load balancing strategies
- ✅ Automatic health checking
- ✅ Failover handling
- ✅ Per-replica connection pools
- ✅ Real-time monitoring

### Polymorphic Relations
- ✅ Generic foreign keys
- ✅ Content type registry
- ✅ STI, JTI, CTI inheritance patterns
- ✅ Polymorphic collections
- ✅ Query helpers

### Migration Tools
- ✅ Data migration utilities
- ✅ Conflict detection
- ✅ Safety validation
- ✅ Automatic rollback
- ✅ Dependency tracking
- ✅ Zero-downtime strategies

---

## 🔄 Breaking Changes

None - All new features are additive and backward compatible with v0.7.0.

---

## 📖 Documentation

All new features include comprehensive documentation:
- In-code docstrings with examples
- Usage examples in each module
- Type hints for IDE support

---

## 🚀 Getting Started

### CLI Tools
```bash
# Inspect database
python -m fastapi_orm inspect --database-url "sqlite:///./app.db"

# Generate models
python -m fastapi_orm generate-models --database-url "postgresql://..." --output models.py

# Scaffold API
python -m fastapi_orm scaffold Product --fields "name:str,price:float" --output api.py
```

### Model Factories
```python
from fastapi_orm import ModelFactory, Faker

class UserFactory(ModelFactory):
    class Meta:
        model = User
    username = Faker('user_name')
    email = Faker('email')

users = await UserFactory.create_batch(session, 10)
```

### Validators
```python
from fastapi_orm import email_validator, strong_password

class User(Model):
    email: str = StringField(validators=[email_validator()])
    password: str = StringField(validators=[strong_password()])
```

### Read Replicas
```python
from fastapi_orm import create_replica_manager, with_read_session

manager = create_replica_manager(primary_url, replica_urls)
async with with_read_session(manager) as session:
    users = await User.all(session)
```

---

## 🙏 Acknowledgments

These features are inspired by best practices from:
- Django ORM (factories, validators)
- Factory Boy (test data generation)
- SQLAlchemy (polymorphic relationships)
- Alembic (migration tools)
- PostgreSQL (read replicas, scaling)

---

## 📝 Version

**Version:** 0.8.0  
**Release Date:** October 2025  
**Previous Version:** 0.7.0 (Multi-tenancy & Audit Logging)

---

## 🔗 See Also

- **v0.7.0**: Multi-tenancy & Audit Logging
- **v0.6.0**: Multi-tenancy Support
- **v0.5.0**: Hooks, Indexes, Full-Text Search, Aggregations
- **v0.4.0**: Field Types, Aggregations, Prefetching
- **v0.3.0**: Decimal, UUID, Enum Fields, Monitoring, Caching

---

## 💡 Next Steps

With v0.8.0, FastAPI ORM now provides enterprise-grade features for:
- Rapid application development (CLI tools)
- Comprehensive testing (factories)
- Data integrity (validators)
- High availability (read replicas)
- Flexible data modeling (polymorphic relations)
- Safe schema evolution (migration tools)

Combine these with existing features like multi-tenancy, audit logging, and full-text search for a complete ORM solution!
