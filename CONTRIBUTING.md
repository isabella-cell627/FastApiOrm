# Contributing to FastAPI ORM

Thank you for your interest in contributing to FastAPI ORM! We welcome contributions from the community.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check if the issue already exists in the [issue tracker](https://github.com/Alqudimi/FastApiOrm/issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment details (Python version, OS, database)

### Submitting Changes

1. **Fork the Repository**
   ```bash
   git clone https://github.com/Alqudimi/FastApiOrm.git
   cd FastApiOrm
   ```

2. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/bug-description
   ```

3. **Make Your Changes**
   - Write clean, readable code
   - Follow existing code style and patterns
   - Add tests for new features
   - Update documentation as needed

4. **Test Your Changes**
   ```bash
   pytest tests/ -v
   ```

5. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "Add feature: description of your changes"
   ```

6. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```
   
   Then create a pull request on GitHub.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/Alqudimi/FastApiOrm.git
cd FastApiOrm

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run examples
python examples/basic_usage.py
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints for function parameters and return values
- Write docstrings for public functions and classes
- Keep functions focused and modular

## Adding Features

When adding new features:

1. Add the feature implementation in the appropriate module
2. Create comprehensive tests
3. Add examples in the `examples/` directory
4. Update documentation (README, FEATURES.md, etc.)
5. Add a changelog entry in the appropriate CHANGELOG file

## Testing

- Write unit tests for new features
- Ensure all tests pass before submitting
- Test with both PostgreSQL and SQLite when applicable
- Include async tests using pytest-asyncio

## Documentation

- Update README.md for major features
- Add detailed docstrings with examples
- Create example files for new features
- Update changelog files

## Questions?

If you have questions about contributing, feel free to:
- Open an issue on GitHub
- Email: eng7mi@gmail.com

Thank you for contributing to FastAPI ORM!
