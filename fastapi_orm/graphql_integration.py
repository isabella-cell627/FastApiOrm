"""
GraphQL Integration for FastAPI ORM

This module provides automatic GraphQL schema generation from ORM models
using Strawberry GraphQL. It creates types, queries, and mutations automatically
based on your model definitions.

Features:
- Automatic type generation from models
- Query and mutation generation
- Relationship handling
- Filter and pagination support
- Input type generation
- Seamless FastAPI integration

Example:
    ```python
    from fastapi import FastAPI
    from fastapi_orm import Model, StringField, IntegerField
    from fastapi_orm.graphql_integration import GraphQLManager
    from strawberry.fastapi import GraphQLRouter
    
    class User(Model):
        __tablename__ = "users"
        id: int = IntegerField(primary_key=True)
        username: str = StringField(max_length=100)
        email: str = StringField(max_length=255)
    
    app = FastAPI()
    gql = GraphQLManager()
    
    # Register models
    gql.register_model(User)
    
    # Create GraphQL schema
    schema = gql.create_schema()
    
    # Add GraphQL endpoint
    graphql_app = GraphQLRouter(schema)
    app.include_router(graphql_app, prefix="/graphql")
    ```
"""

from typing import Any, Dict, List, Optional, Type, get_type_hints
from dataclasses import make_dataclass
import strawberry
from strawberry.types import Info
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func


class GraphQLManager:
    """
    Manager for creating GraphQL schemas from ORM models.
    
    Automatically generates Strawberry types, queries, and mutations
    from your FastAPI ORM models.
    """
    
    def __init__(self):
        """Initialize GraphQL manager."""
        self.models: Dict[str, Type] = {}
        self.types: Dict[str, Any] = {}
        self.input_types: Dict[str, Any] = {}
        self.queries: Dict[str, Any] = {}
        self.mutations: Dict[str, Any] = {}
    
    def register_model(
        self,
        model: Type,
        exclude_fields: Optional[List[str]] = None,
        read_only_fields: Optional[List[str]] = None
    ):
        """
        Register a model for GraphQL schema generation.
        
        Args:
            model: The ORM model class to register
            exclude_fields: Fields to exclude from GraphQL type
            read_only_fields: Fields that should only appear in output type
        
        Example:
            ```python
            gql = GraphQLManager()
            gql.register_model(
                User,
                exclude_fields=["password_hash"],
                read_only_fields=["id", "created_at"]
            )
            ```
        """
        exclude_fields = exclude_fields or []
        read_only_fields = read_only_fields or ["id"]
        
        model_name = model.__name__
        self.models[model_name] = model
        
        # Generate types
        self.types[model_name] = self._create_type(model, exclude_fields)
        self.input_types[model_name] = self._create_input_type(
            model,
            exclude_fields + read_only_fields
        )
        
        # Generate queries
        self._create_queries(model, model_name)
        
        # Generate mutations
        self._create_mutations(model, model_name)
    
    def _create_type(
        self,
        model: Type,
        exclude_fields: List[str]
    ) -> Any:
        """Create Strawberry output type from model."""
        type_hints = get_type_hints(model)
        fields = {}
        
        for field_name, field_type in type_hints.items():
            if field_name.startswith("_") or field_name in exclude_fields:
                continue
            
            # Map SQLAlchemy types to GraphQL types
            gql_type = self._map_type(field_type)
            fields[field_name] = gql_type
        
        # Create Strawberry type
        model_type = strawberry.type(
            make_dataclass(
                f"{model.__name__}Type",
                [(name, typ) for name, typ in fields.items()]
            )
        )
        
        return model_type
    
    def _create_input_type(
        self,
        model: Type,
        exclude_fields: List[str]
    ) -> Any:
        """Create Strawberry input type for mutations."""
        type_hints = get_type_hints(model)
        fields = {}
        
        for field_name, field_type in type_hints.items():
            if field_name.startswith("_") or field_name in exclude_fields:
                continue
            
            # Map SQLAlchemy types to GraphQL types (optional for input)
            gql_type = Optional[self._map_type(field_type)]
            fields[field_name] = gql_type
        
        # Create Strawberry input type
        input_type = strawberry.input(
            make_dataclass(
                f"{model.__name__}Input",
                [(name, typ, None) for name, typ in fields.items()]
            )
        )
        
        return input_type
    
    def _map_type(self, python_type: Type) -> Type:
        """Map Python/SQLAlchemy types to GraphQL types."""
        # Handle Optional types
        origin = getattr(python_type, "__origin__", None)
        if origin is not None:
            # For Optional[T], get T
            args = getattr(python_type, "__args__", ())
            if args:
                python_type = args[0]
        
        # Map basic types
        type_mapping = {
            int: int,
            str: str,
            float: float,
            bool: bool,
        }
        
        return type_mapping.get(python_type, str)
    
    def _create_queries(self, model: Type, model_name: str):
        """Create GraphQL queries for a model."""
        model_type = self.types[model_name]
        
        # Get by ID query
        async def get_by_id(
            id: int,
            info: Info
        ) -> Optional[model_type]:
            """Get single record by ID"""
            session: AsyncSession = info.context["session"]
            instance = await model.get(session, id)
            if instance:
                return self._model_to_type(instance, model_type)
            return None
        
        # List all query
        async def list_all(
            limit: Optional[int] = 100,
            offset: Optional[int] = 0,
            info: Info = None
        ) -> List[model_type]:
            """List all records with pagination"""
            session: AsyncSession = info.context["session"]
            instances = await model.all(session, limit=limit, offset=offset)
            return [self._model_to_type(inst, model_type) for inst in instances]
        
        # Count query
        async def count_all(info: Info) -> int:
            """Count total records"""
            session: AsyncSession = info.context["session"]
            return await model.count(session)
        
        self.queries[f"get{model_name}"] = strawberry.field(get_by_id)
        self.queries[f"list{model_name}s"] = strawberry.field(list_all)
        self.queries[f"count{model_name}s"] = strawberry.field(count_all)
    
    def _create_mutations(self, model: Type, model_name: str):
        """Create GraphQL mutations for a model."""
        model_type = self.types[model_name]
        input_type = self.input_types[model_name]
        
        # Create mutation
        async def create_mutation(
            input: input_type,
            info: Info
        ) -> model_type:
            """Create a new record"""
            session: AsyncSession = info.context["session"]
            
            # Convert input to dict, excluding None values
            data = {
                k: v for k, v in input.__dict__.items()
                if v is not None and not k.startswith("_")
            }
            
            instance = await model.create(session, **data)
            return self._model_to_type(instance, model_type)
        
        # Update mutation
        async def update_mutation(
            id: int,
            input: input_type,
            info: Info
        ) -> Optional[model_type]:
            """Update an existing record"""
            session: AsyncSession = info.context["session"]
            
            # Convert input to dict, excluding None values
            data = {
                k: v for k, v in input.__dict__.items()
                if v is not None and not k.startswith("_")
            }
            
            instance = await model.update_by_id(session, id, **data)
            if instance:
                return self._model_to_type(instance, model_type)
            return None
        
        # Delete mutation
        async def delete_mutation(
            id: int,
            info: Info
        ) -> bool:
            """Delete a record"""
            session: AsyncSession = info.context["session"]
            return await model.delete_by_id(session, id)
        
        self.mutations[f"create{model_name}"] = strawberry.mutation(create_mutation)
        self.mutations[f"update{model_name}"] = strawberry.mutation(update_mutation)
        self.mutations[f"delete{model_name}"] = strawberry.mutation(delete_mutation)
    
    def _model_to_type(self, instance: Any, type_class: Type) -> Any:
        """Convert ORM model instance to GraphQL type."""
        data = {}
        for field_name in type_class.__annotations__.keys():
            if hasattr(instance, field_name):
                data[field_name] = getattr(instance, field_name)
        return type_class(**data)
    
    def create_schema(self) -> Any:
        """
        Create the complete GraphQL schema.
        
        Returns:
            Strawberry Schema object ready to use with FastAPI
        
        Example:
            ```python
            schema = gql.create_schema()
            graphql_app = GraphQLRouter(schema)
            app.include_router(graphql_app, prefix="/graphql")
            ```
        """
        # Create Query class
        Query = strawberry.type(
            type(
                "Query",
                (),
                self.queries
            )
        )
        
        # Create Mutation class
        Mutation = strawberry.type(
            type(
                "Mutation",
                (),
                self.mutations
            )
        )
        
        # Create schema
        schema = strawberry.Schema(
            query=Query,
            mutation=Mutation
        )
        
        return schema


def create_graphql_context(session: AsyncSession) -> Dict[str, Any]:
    """
    Create context for GraphQL execution.
    
    Args:
        session: Database session
    
    Returns:
        Context dictionary with session
    
    Example:
        ```python
        from fastapi import Depends
        from fastapi_orm import Database
        
        db = Database("postgresql+asyncpg://...")
        
        async def get_context(
            session: AsyncSession = Depends(db.get_session)
        ):
            return create_graphql_context(session)
        
        graphql_app = GraphQLRouter(schema, context_getter=get_context)
        ```
    """
    return {"session": session}


__all__ = [
    "GraphQLManager",
    "create_graphql_context",
]
