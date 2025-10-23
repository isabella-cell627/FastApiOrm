# FastAPI ORM - API Reference Documentation

Complete API reference documentation for FastAPI ORM library version 0.11.0.

## About This Documentation

This directory contains comprehensive API reference documentation for all modules, classes, functions, and features provided by FastAPI ORM. This documentation is designed for developers who need detailed technical specifications and API signatures.

**Developer:** Abdulaziz Al-Qadimi  
**Email:** eng7mi@gmail.com  
**Repository:** https://github.com/Alqudimi/FastApiOrm  
**GitHub:** https://github.com/Alqudimi

## Documentation Structure

### Core Components
- **[index.md](index.md)** - Main API reference index and overview
- **[database.md](database.md)** - Database connection and session management
- **[models.md](models.md)** - Model class and CRUD operations
- **[fields.md](fields.md)** - Complete field types reference
- **[relationships.md](relationships.md)** - Relationship definitions and usage

### Query & Data Operations
- **[queries.md](queries.md)** - Advanced querying and filtering
- **[pagination.md](pagination.md)** - Pagination strategies
- **[bulk_operations.md](bulk_operations.md)** - Bulk create, update, delete

### Data Management
- **[transactions.md](transactions.md)** - Transaction management and patterns
- **[validators.md](validators.md)** - Field validation API
- **[exceptions.md](exceptions.md)** - Exception hierarchy and error handling

### Advanced Features
- **[mixins.md](mixins.md)** - Reusable model mixins
- **[caching.md](caching.md)** - Query caching systems

## How to Use This Documentation

### For Beginners
If you're new to FastAPI ORM, start with:
1. [index.md](index.md) - Overview and quick links
2. [database.md](database.md) - Setting up database connection
3. [models.md](models.md) - Creating and using models
4. [fields.md](fields.md) - Available field types

Then explore the **Usage Guides** in `doc/usage-guide/` for step-by-step tutorials.

### For Experienced Developers
Jump directly to the specific module documentation you need:
- Looking for field types? → [fields.md](fields.md)
- Need to optimize queries? → [queries.md](queries.md)
- Working with transactions? → [transactions.md](transactions.md)
- Implementing caching? → [caching.md](caching.md)

### Quick Reference
Each documentation file follows this structure:
1. **Overview** - Brief introduction to the module
2. **Classes/Functions** - Detailed API specifications
3. **Parameters** - Parameter descriptions and types
4. **Returns** - Return values and types
5. **Examples** - Code examples for common use cases
6. **Best Practices** - Recommended patterns and tips
7. **See Also** - Related documentation links

## Documentation Conventions

### Type Annotations
All code examples include type annotations:
```python
async def get_user(session: AsyncSession, user_id: int) -> Optional[User]:
    return await User.get(session, user_id)
```

### Parameter Descriptions
- **Required parameters** are listed without default values
- **Optional parameters** include default values and are marked as optional
- **Type hints** follow Python typing conventions

### Code Examples
- Examples are complete and runnable
- Imports are shown when necessary
- Comments explain complex logic

## Additional Resources

### Usage Guides
For step-by-step tutorials and guides, see:
- `doc/usage-guide/` - Comprehensive usage documentation

### Examples
For working code examples, see:
- `examples/` - Example scripts and applications

### Changelogs
For version history and changes, see:
- `CHANGELOG_V*.md` - Version-specific changelogs in root directory

## Getting Help

### Issues and Questions
- **GitHub Issues:** https://github.com/Alqudimi/FastApiOrm/issues
- **Email:** eng7mi@gmail.com

### Contributing
Contributions to documentation are welcome! Please see `CONTRIBUTING.md` for guidelines.

## Documentation Status

This API reference documentation covers:
- ✅ Core components (Database, Models, Fields, Relationships)
- ✅ Query operations and filtering
- ✅ Data management (Transactions, Validation, Exceptions)
- ✅ Performance features (Caching, Pagination, Bulk Operations)
- ✅ Advanced features (Mixins)
- 📝 Additional modules being documented continuously

## License

This documentation is part of FastAPI ORM, licensed under the MIT License.

---

**Last Updated:** October 2025  
**Documentation Version:** 0.11.0  
**Copyright © 2025 Abdulaziz Al-Qadimi**
