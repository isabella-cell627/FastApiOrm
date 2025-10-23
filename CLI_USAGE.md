# FastAPI ORM CLI Tool

Comprehensive command-line interface for FastAPI ORM database operations.

## Installation

The CLI tool is included with FastAPI ORM. No additional installation required.

## Usage

Run the CLI using Python module syntax:

```bash
python -m fastapi_orm <command> [options]
```

## Available Commands

### Database Operations

#### Create Tables
Create all database tables defined in your models:

```bash
python -m fastapi_orm db-create --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm db-create --database-url "postgresql+asyncpg://user:pass@localhost/mydb" --echo
```

Options:
- `--database-url`: Database connection URL (required)
- `--echo`: Echo SQL statements to console

#### Drop Tables
Drop all database tables (destructive operation):

```bash
python -m fastapi_orm db-drop --database-url "sqlite+aiosqlite:///./app.db" --force
```

Options:
- `--database-url`: Database connection URL (required)
- `--force`: Skip confirmation prompt

#### Reset Database
Drop and recreate all tables:

```bash
python -m fastapi_orm db-reset --database-url "sqlite+aiosqlite:///./app.db" --force
```

Options:
- `--database-url`: Database connection URL (required)
- `--force`: Skip confirmation prompt

### Schema Inspection

#### Inspect Database
Inspect database schema and show table information:

```bash
python -m fastapi_orm inspect --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm inspect --database-url "postgresql://user:pass@localhost/db"
```

Displays:
- All tables in the database
- Column names, types, and nullability
- Primary keys
- Foreign key relationships

### Model Generation

#### Generate Models
Generate SQLAlchemy model code from existing database:

```bash
# Generate all models to stdout
python -m fastapi_orm generate-models --database-url "sqlite+aiosqlite:///./app.db"

# Generate all models to a file
python -m fastapi_orm generate-models --database-url "postgresql://..." --output models.py

# Generate a single model
python -m fastapi_orm generate-models --database-url "sqlite:///./app.db" --table users --output user_model.py
```

Options:
- `--database-url`: Database connection URL (required)
- `--table`: Generate model for specific table only
- `--output`: Output file path (prints to stdout if not specified)

### CRUD Endpoint Scaffolding

#### Scaffold Endpoints
Generate complete CRUD API endpoints for a model:

```bash
python -m fastapi_orm scaffold User --fields "name:str,email:str,age:int" --output api/users.py
```

Options:
- `model_name`: Name of the model (e.g., User, Product)
- `--fields`: Field definitions in format `name:type,name:type` (required)
- `--output`: Output file path (prints to stdout if not specified)

Supported field types:
- `str` - String field
- `int` - Integer field
- `float` - Float field
- `bool` - Boolean field
- `datetime` - DateTime field
- `date` - Date field

### Migration Management

#### Create Migration
Create a new Alembic migration:

```bash
python -m fastapi_orm create-migration "Add users table" --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm create-migration "Add indexes" --database-url "postgresql://..." --migrations-dir migrations
```

Options:
- `message`: Migration message/description (required)
- `--database-url`: Database connection URL (optional, defaults to sqlite)
- `--migrations-dir`: Directory for migrations (optional, defaults to 'migrations')

#### Run Migrations
Apply pending migrations to database:

```bash
python -m fastapi_orm upgrade --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm upgrade --database-url "postgresql://..." --migrations-dir migrations
```

Options:
- `--database-url`: Database connection URL (optional, defaults to sqlite)
- `--migrations-dir`: Directory containing migrations (optional, defaults to 'migrations')

### Health Checks

#### Check Database Health
Run comprehensive health checks on the database:

```bash
python -m fastapi_orm health --database-url "sqlite+aiosqlite:///./app.db"
python -m fastapi_orm health --database-url "postgresql://..." --verbose
```

Options:
- `--database-url`: Database connection URL (required)
- `--verbose`: Show detailed metrics and information

Health check includes:
- Database connectivity
- Connection pool status
- Pool utilization and saturation
- Active/idle connection counts
- Average checkout times

## Examples

### Complete Workflow Example

```bash
# 1. Inspect existing database
python -m fastapi_orm inspect --database-url "postgresql://user:pass@localhost/mydb"

# 2. Generate models from schema
python -m fastapi_orm generate-models --database-url "postgresql://user:pass@localhost/mydb" --output models.py

# 3. Create a new migration
python -m fastapi_orm create-migration "Initial schema" --database-url "postgresql://user:pass@localhost/mydb"

# 4. Apply migrations
python -m fastapi_orm upgrade --database-url "postgresql://user:pass@localhost/mydb"

# 5. Scaffold CRUD endpoints
python -m fastapi_orm scaffold Product --fields "name:str,price:float,stock:int" --output api/products.py

# 6. Check database health
python -m fastapi_orm health --database-url "postgresql://user:pass@localhost/mydb" --verbose
```

### Development Workflow

```bash
# Create tables for development
python -m fastapi_orm db-create --database-url "sqlite+aiosqlite:///./dev.db" --echo

# Reset database when needed
python -m fastapi_orm db-reset --database-url "sqlite+aiosqlite:///./dev.db" --force

# Check health before deployment
python -m fastapi_orm health --database-url "postgresql://..." --verbose
```

## Database URL Format

The `--database-url` parameter accepts standard SQLAlchemy database URLs:

**SQLite (async):**
```
sqlite+aiosqlite:///./database.db
```

**PostgreSQL (async):**
```
postgresql+asyncpg://username:password@host:port/database
```

**MySQL (async):**
```
mysql+aiomysql://username:password@host:port/database
```

## Tips

1. **Use Environment Variables**: Store your database URL in an environment variable:
   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:pass@localhost/db"
   python -m fastapi_orm health --database-url "$DATABASE_URL"
   ```

2. **Always Use `--force` Carefully**: The `--force` flag skips confirmation prompts for destructive operations. Use with caution in production.

3. **Echo SQL for Debugging**: Use `--echo` with `db-create` to see the generated SQL statements.

4. **Regular Health Checks**: Run `health` command regularly to monitor connection pool status and catch issues early.

5. **Generate Before Scaffold**: Use `generate-models` to create base models from your database, then `scaffold` to create API endpoints.

## Troubleshooting

### Command Not Found

If you get "command not found", ensure you're using the correct syntax:
```bash
python -m fastapi_orm <command>
```

### Database Connection Errors

- Verify your database URL format
- Check that the database server is running
- Ensure you have the correct async driver installed (aiosqlite, asyncpg, etc.)

### Migration Errors

- Ensure Alembic is installed: `pip install alembic`
- Check that your migrations directory exists
- Verify your models are properly imported

## See Also

- [CHANGELOG_V0.11.md](CHANGELOG_V0.11.md) - New features in version 0.11.0
- [Pool Monitoring Example](examples/pool_monitoring_example.py) - Using the health check dashboard
- [FastAPI ORM Documentation](README.md) - Main library documentation
