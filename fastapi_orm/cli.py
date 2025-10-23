"""
CLI Tools for FastAPI ORM

Provides command-line utilities for:
- Generating models from existing databases (reverse engineering)
- Creating and running migrations
- Scaffolding CRUD endpoints
- Interactive model creation
- Database inspection and analysis

Usage:
    python -m fastapi_orm.cli inspect --database-url "sqlite:///./app.db"
    python -m fastapi_orm.cli generate-models --database-url "postgresql://user:pass@localhost/db"
    python -m fastapi_orm.cli scaffold User --fields "username:str,email:str,age:int"
    python -m fastapi_orm.cli create-migration "Add users table"
"""

import argparse
import sys
from typing import Optional, List, Dict, Any
import asyncio
from pathlib import Path
import re


class CLIColors:
    """ANSI color codes for terminal output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_success(message: str):
    """Print success message in green"""
    print(f"{CLIColors.OKGREEN}✓ {message}{CLIColors.ENDC}")


def print_error(message: str):
    """Print error message in red"""
    print(f"{CLIColors.FAIL}✗ {message}{CLIColors.ENDC}", file=sys.stderr)


def print_info(message: str):
    """Print info message in blue"""
    print(f"{CLIColors.OKBLUE}ℹ {message}{CLIColors.ENDC}")


def print_warning(message: str):
    """Print warning message in yellow"""
    print(f"{CLIColors.WARNING}⚠ {message}{CLIColors.ENDC}")


class DatabaseInspector:
    """Inspect existing databases and extract schema information"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = None
        self.inspector = None
    
    async def connect(self):
        """Connect to the database"""
        from sqlalchemy.ext.asyncio import create_async_engine
        from sqlalchemy import inspect
        
        self.engine = create_async_engine(self.database_url, echo=False)
        
        # Use sync connection for inspection
        from sqlalchemy import create_engine
        sync_url = self.database_url.replace('+aiosqlite', '').replace('+asyncpg', '')
        sync_engine = create_engine(sync_url, echo=False)
        self.inspector = inspect(sync_engine)
    
    async def close(self):
        """Close database connection"""
        if self.engine:
            await self.engine.dispose()
    
    def get_tables(self) -> List[str]:
        """Get list of all tables in the database"""
        return self.inspector.get_table_names()
    
    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table"""
        return self.inspector.get_columns(table_name)
    
    def get_primary_keys(self, table_name: str) -> List[str]:
        """Get primary key columns for a table"""
        pk = self.inspector.get_pk_constraint(table_name)
        return pk.get('constrained_columns', [])
    
    def get_foreign_keys(self, table_name: str) -> List[Dict[str, Any]]:
        """Get foreign keys for a table"""
        return self.inspector.get_foreign_keys(table_name)
    
    def get_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        """Get indexes for a table"""
        return self.inspector.get_indexes(table_name)


class ModelGenerator:
    """Generate model code from database schema"""
    
    TYPE_MAPPING = {
        'INTEGER': 'IntegerField',
        'BIGINT': 'IntegerField',
        'SMALLINT': 'IntegerField',
        'VARCHAR': 'StringField',
        'CHAR': 'StringField',
        'TEXT': 'TextField',
        'BOOLEAN': 'BooleanField',
        'FLOAT': 'FloatField',
        'REAL': 'FloatField',
        'DOUBLE': 'FloatField',
        'NUMERIC': 'DecimalField',
        'DECIMAL': 'DecimalField',
        'DATE': 'DateField',
        'TIME': 'TimeField',
        'DATETIME': 'DateTimeField',
        'TIMESTAMP': 'DateTimeField',
        'JSON': 'JSONField',
        'JSONB': 'JSONField',
        'UUID': 'UUIDField',
    }
    
    PYTHON_TYPE_MAPPING = {
        'IntegerField': 'int',
        'StringField': 'str',
        'TextField': 'str',
        'BooleanField': 'bool',
        'FloatField': 'float',
        'DecimalField': 'Decimal',
        'DateField': 'date',
        'TimeField': 'time',
        'DateTimeField': 'datetime',
        'JSONField': 'dict',
        'UUIDField': 'UUID',
    }
    
    def __init__(self, inspector: DatabaseInspector):
        self.inspector = inspector
    
    def _to_field_type(self, sql_type: str) -> str:
        """Convert SQL type to FastAPI ORM field type"""
        sql_type = sql_type.upper()
        for key, value in self.TYPE_MAPPING.items():
            if key in sql_type:
                return value
        return 'StringField'
    
    def _to_class_name(self, table_name: str) -> str:
        """Convert table name to Python class name"""
        return ''.join(word.capitalize() for word in table_name.split('_'))
    
    def generate_model(self, table_name: str) -> str:
        """Generate model code for a table"""
        class_name = self._to_class_name(table_name)
        columns = self.inspector.get_columns(table_name)
        primary_keys = self.inspector.get_primary_keys(table_name)
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        
        # Build field definitions
        field_lines = []
        imports = {'Model', 'IntegerField', 'StringField'}
        
        for col in columns:
            field_name = col['name']
            sql_type = str(col['type'])
            field_type = self._to_field_type(sql_type)
            imports.add(field_type)
            
            # Build field parameters
            params = []
            
            if field_name in primary_keys:
                params.append('primary_key=True')
            
            if not col.get('nullable', True):
                params.append('nullable=False')
            
            if col.get('default') is not None:
                default_val = col['default']
                params.append(f'default={repr(default_val)}')
            
            # Add max_length for string fields
            if field_type == 'StringField' and hasattr(col['type'], 'length') and col['type'].length:
                params.append(f'max_length={col["type"].length}')
            
            # Check for unique constraint
            if col.get('unique', False):
                params.append('unique=True')
            
            param_str = ', '.join(params)
            python_type = self.PYTHON_TYPE_MAPPING.get(field_type, 'Any')
            
            if col.get('nullable', True) and field_name not in primary_keys:
                python_type = f'Optional[{python_type}]'
                imports.add('Optional')
            
            field_line = f'    {field_name}: {python_type} = {field_type}({param_str})'
            field_lines.append(field_line)
        
        # Add foreign key relationships
        relationship_lines = []
        for fk in foreign_keys:
            fk_columns = fk.get('constrained_columns', [])
            ref_table = fk.get('referred_table', '')
            if fk_columns and ref_table:
                rel_name = ref_table.rstrip('s')
                ref_class = self._to_class_name(ref_table)
                relationship_lines.append(f'    {rel_name} = ManyToOne("{ref_class}")')
                imports.add('ManyToOne')
        
        # Build imports
        import_line = f"from fastapi_orm import {', '.join(sorted(imports))}"
        if 'Optional' in imports:
            import_line = f"from typing import Optional, Any\n{import_line}"
        
        # Build model class
        model_code = f'''{import_line}


class {class_name}(Model):
    __tablename__ = "{table_name}"

{chr(10).join(field_lines)}
'''
        
        if relationship_lines:
            model_code += '\n' + '\n'.join(relationship_lines) + '\n'
        
        return model_code
    
    def generate_all_models(self, output_file: Optional[str] = None) -> str:
        """Generate models for all tables in the database"""
        tables = self.inspector.get_tables()
        
        models_code = '"""\nAuto-generated models from database schema\nGenerated by FastAPI ORM CLI\n"""\n\n'
        
        # Collect all imports
        all_imports = set()
        model_codes = []
        
        for table in tables:
            model_code = self.generate_model(table)
            model_codes.append(model_code)
        
        # Combine all models
        full_code = models_code + '\n\n'.join(model_codes)
        
        if output_file:
            Path(output_file).write_text(full_code)
            print_success(f"Generated models written to {output_file}")
        
        return full_code


class EndpointScaffolder:
    """Generate FastAPI CRUD endpoints for models"""
    
    def __init__(self, model_name: str, fields: Dict[str, str]):
        self.model_name = model_name
        self.fields = fields
    
    def generate_pydantic_schemas(self) -> str:
        """Generate Pydantic request/response schemas"""
        field_lines = []
        for field_name, field_type in self.fields.items():
            python_type = self._python_type(field_type)
            field_lines.append(f'    {field_name}: {python_type}')
        
        return f'''
class {self.model_name}Create(BaseModel):
{chr(10).join(field_lines)}


class {self.model_name}Update(BaseModel):
{chr(10).join(field_lines)}


class {self.model_name}Response(BaseModel):
    id: int
{chr(10).join(field_lines)}
    
    class Config:
        from_attributes = True
'''
    
    def generate_endpoints(self) -> str:
        """Generate CRUD endpoints"""
        lower_name = self.model_name.lower()
        plural_name = f"{lower_name}s"
        
        return f'''
@app.post("/{plural_name}", response_model={self.model_name}Response, status_code=201)
async def create_{lower_name}(
    data: {self.model_name}Create,
    session: AsyncSession = Depends(get_db)
):
    """Create a new {lower_name}"""
    {lower_name} = await {self.model_name}.create(session, **data.model_dump())
    return {lower_name}.to_response()


@app.get("/{plural_name}", response_model=List[{self.model_name}Response])
async def list_{plural_name}(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db)
):
    """List all {plural_name}"""
    {plural_name} = await {self.model_name}.all(session, limit=limit, offset=skip)
    return [{lower_name}.to_response() for {lower_name} in {plural_name}]


@app.get("/{plural_name}/{{id}}", response_model={self.model_name}Response)
async def get_{lower_name}(
    id: int,
    session: AsyncSession = Depends(get_db)
):
    """Get a specific {lower_name} by ID"""
    {lower_name} = await {self.model_name}.get(session, id)
    if not {lower_name}:
        raise HTTPException(status_code=404, detail="{self.model_name} not found")
    return {lower_name}.to_response()


@app.put("/{plural_name}/{{id}}", response_model={self.model_name}Response)
async def update_{lower_name}(
    id: int,
    data: {self.model_name}Update,
    session: AsyncSession = Depends(get_db)
):
    """Update a {lower_name}"""
    {lower_name} = await {self.model_name}.update_by_id(session, id, **data.model_dump())
    if not {lower_name}:
        raise HTTPException(status_code=404, detail="{self.model_name} not found")
    return {lower_name}.to_response()


@app.delete("/{plural_name}/{{id}}", status_code=204)
async def delete_{lower_name}(
    id: int,
    session: AsyncSession = Depends(get_db)
):
    """Delete a {lower_name}"""
    deleted = await {self.model_name}.delete_by_id(session, id)
    if not deleted:
        raise HTTPException(status_code=404, detail="{self.model_name} not found")
    return None
'''
    
    def _python_type(self, field_type: str) -> str:
        """Convert field type string to Python type annotation"""
        type_map = {
            'str': 'str',
            'string': 'str',
            'int': 'int',
            'integer': 'int',
            'float': 'float',
            'bool': 'bool',
            'boolean': 'bool',
            'datetime': 'datetime',
            'date': 'date',
            'time': 'time',
            'dict': 'dict',
            'json': 'dict',
        }
        return type_map.get(field_type.lower(), 'str')
    
    def generate_full_api(self, output_file: Optional[str] = None) -> str:
        """Generate complete API file with all endpoints"""
        code = f'''"""
Auto-generated CRUD API for {self.model_name}
Generated by FastAPI ORM CLI
"""

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi_orm import Database, Model
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List
from datetime import datetime, date, time


# Database setup
db = Database("sqlite+aiosqlite:///./app.db")


async def get_db():
    async for session in db.get_session():
        yield session


app = FastAPI(title="{self.model_name} API")

{self.generate_pydantic_schemas()}
{self.generate_endpoints()}


@app.on_event("startup")
async def startup():
    await db.create_tables()


@app.on_event("shutdown")
async def shutdown():
    await db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
'''
        
        if output_file:
            Path(output_file).write_text(code)
            print_success(f"Generated API written to {output_file}")
        
        return code


def parse_fields(fields_str: str) -> Dict[str, str]:
    """Parse field definitions from string like 'name:str,age:int,email:str'"""
    fields = {}
    for field_def in fields_str.split(','):
        field_def = field_def.strip()
        if ':' in field_def:
            name, ftype = field_def.split(':', 1)
            fields[name.strip()] = ftype.strip()
    return fields


async def inspect_command(args):
    """Inspect database and show schema information"""
    print_info(f"Inspecting database: {args.database_url}")
    
    inspector = DatabaseInspector(args.database_url)
    await inspector.connect()
    
    try:
        tables = inspector.get_tables()
        print_success(f"Found {len(tables)} tables\n")
        
        for table in tables:
            print(f"\n{CLIColors.BOLD}Table: {table}{CLIColors.ENDC}")
            print("─" * 80)
            
            columns = inspector.get_columns(table)
            primary_keys = inspector.get_primary_keys(table)
            foreign_keys = inspector.get_foreign_keys(table)
            
            print(f"\n  {CLIColors.UNDERLINE}Columns:{CLIColors.ENDC}")
            for col in columns:
                pk_marker = " [PK]" if col['name'] in primary_keys else ""
                nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                print(f"    • {col['name']}: {col['type']} {nullable}{pk_marker}")
            
            if foreign_keys:
                print(f"\n  {CLIColors.UNDERLINE}Foreign Keys:{CLIColors.ENDC}")
                for fk in foreign_keys:
                    constrained = ', '.join(fk.get('constrained_columns', []))
                    referred = fk.get('referred_table', '')
                    referred_cols = ', '.join(fk.get('referred_columns', []))
                    print(f"    • {constrained} → {referred}({referred_cols})")
    
    finally:
        await inspector.close()


async def generate_models_command(args):
    """Generate model code from database schema"""
    print_info(f"Generating models from: {args.database_url}")
    
    inspector = DatabaseInspector(args.database_url)
    await inspector.connect()
    
    try:
        generator = ModelGenerator(inspector)
        
        if args.table:
            # Generate single model
            code = generator.generate_model(args.table)
            print("\n" + code)
            
            if args.output:
                Path(args.output).write_text(code)
                print_success(f"Model written to {args.output}")
        else:
            # Generate all models
            code = generator.generate_all_models(args.output)
            if not args.output:
                print("\n" + code)
    
    finally:
        await inspector.close()


def scaffold_command(args):
    """Scaffold CRUD endpoints for a model"""
    print_info(f"Scaffolding CRUD endpoints for {args.model_name}")
    
    fields = parse_fields(args.fields)
    
    if not fields:
        print_error("No fields provided. Use format: name:str,age:int,email:str")
        return
    
    print_info(f"Fields: {', '.join(f'{k}:{v}' for k, v in fields.items())}")
    
    scaffolder = EndpointScaffolder(args.model_name, fields)
    code = scaffolder.generate_full_api(args.output)
    
    if not args.output:
        print("\n" + code)


def create_migration_command(args):
    """Create a new migration"""
    from .migrations import MigrationManager
    
    print_info(f"Creating migration: {args.message}")
    
    manager = MigrationManager(
        database_url=args.database_url or "sqlite+aiosqlite:///./app.db",
        migrations_dir=args.migrations_dir or "migrations"
    )
    
    try:
        manager.create_migration(args.message)
        print_success("Migration created successfully")
    except Exception as e:
        print_error(f"Failed to create migration: {e}")


def upgrade_command(args):
    """Run migrations"""
    from .migrations import MigrationManager
    
    print_info("Running database migrations...")
    
    manager = MigrationManager(
        database_url=args.database_url or "sqlite+aiosqlite:///./app.db",
        migrations_dir=args.migrations_dir or "migrations"
    )
    
    try:
        manager.upgrade()
        print_success("Migrations completed successfully")
    except Exception as e:
        print_error(f"Migration failed: {e}")


async def db_create_command(args):
    """Create all database tables"""
    from .database import Database
    
    print_info(f"Creating tables in {args.database_url}")
    db = Database(args.database_url, echo=args.echo)
    
    try:
        await db.create_tables()
        print_success("Tables created successfully")
    except Exception as e:
        print_error(f"Failed to create tables: {e}")
        sys.exit(1)


async def db_drop_command(args):
    """Drop all database tables"""
    from .database import Database
    
    if not args.force:
        response = input(f"Are you sure you want to drop all tables in {args.database_url}? (yes/no): ")
        if response.lower() != "yes":
            print_warning("Operation cancelled")
            return
    
    print_info(f"Dropping tables from {args.database_url}")
    db = Database(args.database_url)
    
    try:
        await db.drop_tables()
        print_success("Tables dropped successfully")
    except Exception as e:
        print_error(f"Failed to drop tables: {e}")
        sys.exit(1)


async def db_reset_command(args):
    """Drop and recreate all tables"""
    from .database import Database
    
    if not args.force:
        response = input(f"Are you sure you want to reset database {args.database_url}? (yes/no): ")
        if response.lower() != "yes":
            print_warning("Operation cancelled")
            return
    
    print_info(f"Resetting database {args.database_url}")
    db = Database(args.database_url)
    
    try:
        await db.drop_tables()
        await db.create_tables()
        print_success("Database reset successfully")
    except Exception as e:
        print_error(f"Failed to reset database: {e}")
        sys.exit(1)


async def health_command(args):
    """Run health checks"""
    from .database import Database
    from .pool_monitoring import PoolMonitor
    
    print_info(f"Running health checks on {args.database_url}")
    db = Database(args.database_url)
    monitor = PoolMonitor(db)
    
    try:
        health = await monitor.get_health()
        
        status_color = CLIColors.OKGREEN if health['status'] == 'healthy' else CLIColors.WARNING if health['status'] == 'degraded' else CLIColors.FAIL
        print(f"\nStatus: {status_color}{health['status'].upper()}{CLIColors.ENDC}")
        print(f"Message: {health['message']}")
        print(f"\nChecks:")
        for check_name, check_data in health['checks'].items():
            status_symbol = "✓" if check_data['status'] == 'healthy' else "✗"
            color = CLIColors.OKGREEN if check_data['status'] == 'healthy' else CLIColors.WARNING
            print(f"  {color}{status_symbol} {check_name}: {check_data['message']}{CLIColors.ENDC}")
        
        if args.verbose:
            print(f"\nMetrics:")
            for key, value in health['metrics'].items():
                print(f"  {key}: {value}")
    except Exception as e:
        print_error(f"Health check failed: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="FastAPI ORM CLI Tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Inspect database
  fastapi-orm inspect --database-url "sqlite:///./app.db"
  
  # Generate models from database
  fastapi-orm generate-models --database-url "postgresql://user:pass@localhost/db" --output models.py
  
  # Generate single model
  fastapi-orm generate-models --database-url "sqlite:///./app.db" --table users --output user_model.py
  
  # Scaffold CRUD endpoints
  fastapi-orm scaffold User --fields "name:str,email:str,age:int" --output api/users.py
  
  # Create migration
  fastapi-orm create-migration "Add users table" --database-url "sqlite:///./app.db"
  
  # Run migrations
  fastapi-orm upgrade --database-url "sqlite:///./app.db"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Inspect command
    inspect_parser = subparsers.add_parser('inspect', help='Inspect database schema')
    inspect_parser.add_argument('--database-url', required=True, help='Database URL')
    
    # Generate models command
    gen_parser = subparsers.add_parser('generate-models', help='Generate models from database')
    gen_parser.add_argument('--database-url', required=True, help='Database URL')
    gen_parser.add_argument('--table', help='Generate model for specific table only')
    gen_parser.add_argument('--output', '-o', help='Output file path')
    
    # Scaffold command
    scaffold_parser = subparsers.add_parser('scaffold', help='Scaffold CRUD endpoints')
    scaffold_parser.add_argument('model_name', help='Model name (e.g., User, Product)')
    scaffold_parser.add_argument('--fields', '-f', required=True, help='Fields in format: name:str,age:int,email:str')
    scaffold_parser.add_argument('--output', '-o', help='Output file path')
    
    # Create migration command
    migration_parser = subparsers.add_parser('create-migration', help='Create a new migration')
    migration_parser.add_argument('message', help='Migration message')
    migration_parser.add_argument('--database-url', help='Database URL')
    migration_parser.add_argument('--migrations-dir', default='migrations', help='Migrations directory')
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser('upgrade', help='Run database migrations')
    upgrade_parser.add_argument('--database-url', help='Database URL')
    upgrade_parser.add_argument('--migrations-dir', default='migrations', help='Migrations directory')
    
    # Database operations
    db_create_parser = subparsers.add_parser('db-create', help='Create all database tables')
    db_create_parser.add_argument('--database-url', required=True, help='Database URL')
    db_create_parser.add_argument('--echo', action='store_true', help='Echo SQL statements')
    
    db_drop_parser = subparsers.add_parser('db-drop', help='Drop all database tables')
    db_drop_parser.add_argument('--database-url', required=True, help='Database URL')
    db_drop_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    db_reset_parser = subparsers.add_parser('db-reset', help='Reset database (drop and recreate)')
    db_reset_parser.add_argument('--database-url', required=True, help='Database URL')
    db_reset_parser.add_argument('--force', action='store_true', help='Skip confirmation')
    
    # Health check
    health_parser = subparsers.add_parser('health', help='Check database health')
    health_parser.add_argument('--database-url', required=True, help='Database URL')
    health_parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'inspect':
        asyncio.run(inspect_command(args))
    elif args.command == 'generate-models':
        asyncio.run(generate_models_command(args))
    elif args.command == 'scaffold':
        scaffold_command(args)
    elif args.command == 'create-migration':
        create_migration_command(args)
    elif args.command == 'upgrade':
        upgrade_command(args)
    elif args.command == 'db-create':
        asyncio.run(db_create_command(args))
    elif args.command == 'db-drop':
        asyncio.run(db_drop_command(args))
    elif args.command == 'db-reset':
        asyncio.run(db_reset_command(args))
    elif args.command == 'health':
        asyncio.run(health_command(args))


if __name__ == '__main__':
    main()
