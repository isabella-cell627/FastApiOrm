from fastapi_orm.database import Database, Base
from fastapi_orm.model import Model
from fastapi_orm.fields import (
    IntegerField,
    StringField,
    TextField,
    BooleanField,
    FloatField,
    DateTimeField,
    DateField,
    TimeField,
    JSONField,
    DecimalField,
    UUIDField,
    EnumField,
    ArrayField,
)
from fastapi_orm.relations import (
    ForeignKeyField,
    OneToMany,
    ManyToOne,
    ManyToMany,
    create_association_table,
)
from fastapi_orm.migrations import MigrationManager
from fastapi_orm.mixins import SoftDeleteMixin, TimestampMixin
from fastapi_orm.exceptions import (
    FastAPIOrmException,
    RecordNotFoundError,
    DuplicateRecordError,
    ValidationError,
    DatabaseError,
    TransactionError,
)
from fastapi_orm.transactions import transactional, transaction, atomic
from fastapi_orm.cache import QueryCache, get_cache, clear_cache
from fastapi_orm.rate_limit import (
    RateLimiter,
    RateLimitConfig,
    RateLimitMiddleware,
    TokenBucket,
    SlidingWindowCounter,
    FixedWindowCounter,
    TieredRateLimiter,
    rate_limit,
)
from fastapi_orm.streaming import (
    QueryStreamer,
    CursorPaginator,
    BatchProcessor,
    stream_with_transform,
    stream_with_filter,
)
from fastapi_orm.seeding import Seeder, random_string, random_email, random_username, random_text, random_int, random_float, random_bool, random_choice, sequential
from fastapi_orm.constraints import create_composite_primary_key, create_composite_unique, create_composite_index, create_check_constraint
from fastapi_orm.monitoring import QueryMonitor, get_monitor
from fastapi_orm.query import Q
from fastapi_orm.hooks import (
    HooksMixin,
    get_signals,
    receiver,
    Signal,
)
from fastapi_orm.indexes import (
    Index,
    create_index,
    create_partial_index,
    create_gin_index,
    create_btree_index,
    create_hash_index,
    create_covering_index,
    indexes,
)
from fastapi_orm.json_ops import (
    json_contains,
    json_contained_by,
    json_has_key,
    json_has_any_key,
    json_has_all_keys,
    json_path,
    json_path_exists,
)
from fastapi_orm.fulltext import (
    create_search_vector,
    ts_query,
    ts_rank,
    ts_headline,
    SearchQuery,
    create_search_trigger,
    FullTextSearchMixin,
)
from fastapi_orm.resilience import (
    RetryConfig,
    CircuitBreaker,
    get_circuit_breaker,
    with_retry,
    resilient_connect,
    wait_for_database,
)
from fastapi_orm.abstract import AbstractModel, create_abstract_model
from fastapi_orm.aggregations import AggregateQuery, AggregationMixin
from fastapi_orm.tenancy import (
    TenantMixin,
    set_current_tenant,
    get_current_tenant,
    clear_current_tenant,
    require_tenant,
    TenantIsolationError,
    tenant_filter,
    bypass_tenant_filter,
    SchemaBasedTenancy,
    TenantAwareSession,
    get_all_tenants,
)
from fastapi_orm.audit import (
    AuditMixin,
    AuditLog,
    set_audit_user,
    get_audit_user,
    clear_audit_user,
    get_audit_trail,
    get_user_activity,
    get_recent_changes,
    search_audit_logs,
)
from fastapi_orm.factories import (
    ModelFactory,
    Faker,
    Sequence,
    LazyAttribute,
    SubFactory,
    faker,
    sequence,
    lazy_attribute,
    subfactory,
)
from fastapi_orm.validators import (
    Validator,
    AsyncValidator,
    ValidationError as ValidatorError,
    LengthValidator,
    RangeValidator,
    RegexValidator,
    EmailValidator,
    URLValidator,
    PhoneValidator,
    CreditCardValidator,
    IPAddressValidator,
    ChoiceValidator,
    DateRangeValidator,
    PasswordStrengthValidator,
    UniqueValidator,
    ConditionalValidator,
    min_length,
    max_length,
    length_range,
    min_value,
    max_value,
    value_range,
    email_validator,
    url_validator,
    phone_validator,
    credit_card_validator,
    ip_address_validator,
    choice_validator,
    regex_validator,
    strong_password,
    unique_validator,
    validate_if,
    date_range_validator,
    cross_field_validator,
)
from fastapi_orm.read_replicas import (
    ReplicaManager,
    ReplicaInfo,
    LoadBalancer,
    ReplicaStrategy,
    ReplicaStatus,
    ReadWriteSession,
    create_replica_manager,
    with_read_session,
    with_write_session,
)
from fastapi_orm.polymorphic import (
    PolymorphicMixin,
    GenericForeignKey,
    ContentTypeRegistry,
    PolymorphicQuery,
    PolymorphicCollection,
    STIMixin,
    JTIMixin,
    register_model,
    get_model_by_type,
    get_polymorphic_object,
    create_generic_relation,
)
from fastapi_orm.migration_tools import (
    DataMigration,
    MigrationValidator,
    SafeMigrator,
    MigrationDependencyGraph,
    ZeroDowntimeMigration,
    MigrationConflict,
    MigrationValidationError,
)
from fastapi_orm.utils import (
    UtilsMixin,
    OptimisticLockMixin,
)
from fastapi_orm.pool_monitoring import (
    PoolMonitor,
    HealthCheckRouter,
    ConnectionMetrics,
)
from fastapi_orm.composite_keys import (
    composite_primary_key,
    composite_unique,
    check_constraint,
    CompositeKeyMixin,
    constraints,
)

# Optional imports - only available if dependencies are installed
try:
    from fastapi_orm.graphql_integration import (
        GraphQLManager,
        create_graphql_context,
    )
except ImportError:
    GraphQLManager = None
    create_graphql_context = None

try:
    from fastapi_orm.file_upload import (
        FileManager,
        LocalStorage,
        S3Storage,
        UploadResult,
        ImageProcessor,
    )
except ImportError:
    FileManager = None
    LocalStorage = None
    S3Storage = None
    UploadResult = None
    ImageProcessor = None

try:
    from fastapi_orm.middleware import (
        RequestIDMiddleware,
        RequestLoggingMiddleware,
        PerformanceMiddleware,
        ErrorTrackingMiddleware,
        CORSHeadersMiddleware,
    )
except ImportError:
    RequestIDMiddleware = None
    RequestLoggingMiddleware = None
    PerformanceMiddleware = None
    ErrorTrackingMiddleware = None
    CORSHeadersMiddleware = None

try:
    from fastapi_orm.distributed_cache import DistributedCache, HybridCache
except ImportError:
    DistributedCache = None
    HybridCache = None

try:
    from fastapi_orm.websocket import (
        ConnectionManager,
        WebSocketEventFilter,
        WebSocketSubscriptionManager,
        websocket_lifespan,
        create_websocket_route_handler,
    )
except ImportError:
    ConnectionManager = None
    WebSocketEventFilter = None
    WebSocketSubscriptionManager = None
    websocket_lifespan = None
    create_websocket_route_handler = None

__version__ = "0.11.0"

__all__ = [
    "Database",
    "Base",
    "Model",
    "IntegerField",
    "StringField",
    "TextField",
    "BooleanField",
    "FloatField",
    "DateTimeField",
    "DateField",
    "TimeField",
    "JSONField",
    "DecimalField",
    "UUIDField",
    "EnumField",
    "ArrayField",
    "ForeignKeyField",
    "OneToMany",
    "ManyToOne",
    "ManyToMany",
    "create_association_table",
    "MigrationManager",
    "SoftDeleteMixin",
    "TimestampMixin",
    "FastAPIOrmException",
    "RecordNotFoundError",
    "DuplicateRecordError",
    "ValidationError",
    "DatabaseError",
    "TransactionError",
    "transactional",
    "transaction",
    "atomic",
    "QueryCache",
    "get_cache",
    "clear_cache",
    "DistributedCache",
    "HybridCache",
    "ConnectionManager",
    "WebSocketEventFilter",
    "WebSocketSubscriptionManager",
    "websocket_lifespan",
    "create_websocket_route_handler",
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitMiddleware",
    "TokenBucket",
    "SlidingWindowCounter",
    "FixedWindowCounter",
    "TieredRateLimiter",
    "rate_limit",
    "QueryStreamer",
    "CursorPaginator",
    "BatchProcessor",
    "stream_with_transform",
    "stream_with_filter",
    "Seeder",
    "random_string",
    "random_email",
    "random_username",
    "random_text",
    "random_int",
    "random_float",
    "random_bool",
    "random_choice",
    "sequential",
    "create_composite_primary_key",
    "create_composite_unique",
    "create_composite_index",
    "create_check_constraint",
    "QueryMonitor",
    "get_monitor",
    "Q",
    "HooksMixin",
    "get_signals",
    "receiver",
    "Signal",
    "Index",
    "create_index",
    "create_partial_index",
    "create_gin_index",
    "create_btree_index",
    "create_hash_index",
    "create_covering_index",
    "indexes",
    "json_contains",
    "json_contained_by",
    "json_has_key",
    "json_has_any_key",
    "json_has_all_keys",
    "json_path",
    "json_path_exists",
    "create_search_vector",
    "ts_query",
    "ts_rank",
    "ts_headline",
    "SearchQuery",
    "create_search_trigger",
    "FullTextSearchMixin",
    "RetryConfig",
    "CircuitBreaker",
    "get_circuit_breaker",
    "with_retry",
    "resilient_connect",
    "wait_for_database",
    "AbstractModel",
    "create_abstract_model",
    "AggregateQuery",
    "AggregationMixin",
    "TenantMixin",
    "set_current_tenant",
    "get_current_tenant",
    "clear_current_tenant",
    "require_tenant",
    "TenantIsolationError",
    "tenant_filter",
    "bypass_tenant_filter",
    "SchemaBasedTenancy",
    "TenantAwareSession",
    "get_all_tenants",
    "AuditMixin",
    "AuditLog",
    "set_audit_user",
    "get_audit_user",
    "clear_audit_user",
    "get_audit_trail",
    "get_user_activity",
    "get_recent_changes",
    "search_audit_logs",
    "ModelFactory",
    "Faker",
    "Sequence",
    "LazyAttribute",
    "SubFactory",
    "faker",
    "sequence",
    "lazy_attribute",
    "subfactory",
    "Validator",
    "AsyncValidator",
    "ValidatorError",
    "LengthValidator",
    "RangeValidator",
    "RegexValidator",
    "EmailValidator",
    "URLValidator",
    "PhoneValidator",
    "CreditCardValidator",
    "IPAddressValidator",
    "ChoiceValidator",
    "DateRangeValidator",
    "PasswordStrengthValidator",
    "UniqueValidator",
    "ConditionalValidator",
    "min_length",
    "max_length",
    "length_range",
    "min_value",
    "max_value",
    "value_range",
    "email_validator",
    "url_validator",
    "phone_validator",
    "credit_card_validator",
    "ip_address_validator",
    "choice_validator",
    "regex_validator",
    "strong_password",
    "unique_validator",
    "validate_if",
    "date_range_validator",
    "cross_field_validator",
    "ReplicaManager",
    "ReplicaInfo",
    "LoadBalancer",
    "ReplicaStrategy",
    "ReplicaStatus",
    "ReadWriteSession",
    "create_replica_manager",
    "with_read_session",
    "with_write_session",
    "PolymorphicMixin",
    "GenericForeignKey",
    "ContentTypeRegistry",
    "PolymorphicQuery",
    "PolymorphicCollection",
    "STIMixin",
    "JTIMixin",
    "register_model",
    "get_model_by_type",
    "get_polymorphic_object",
    "create_generic_relation",
    "DataMigration",
    "MigrationValidator",
    "SafeMigrator",
    "MigrationDependencyGraph",
    "ZeroDowntimeMigration",
    "MigrationConflict",
    "MigrationValidationError",
    "UtilsMixin",
    "OptimisticLockMixin",
    "PoolMonitor",
    "HealthCheckRouter",
    "ConnectionMetrics",
    "composite_primary_key",
    "composite_unique",
    "check_constraint",
    "CompositeKeyMixin",
    "constraints",
    "GraphQLManager",
    "create_graphql_context",
    "FileManager",
    "LocalStorage",
    "S3Storage",
    "UploadResult",
    "ImageProcessor",
    "RequestIDMiddleware",
    "RequestLoggingMiddleware",
    "PerformanceMiddleware",
    "ErrorTrackingMiddleware",
    "CORSHeadersMiddleware",
]
