# Publishing Guide for FastAPI ORM

This guide explains how to publish your FastAPI ORM package to GitHub and PyPI.

## Prerequisites

- GitHub account
- PyPI account (https://pypi.org/account/register/)
- Git installed locally
- Python 3.11+ with pip

## Publishing to GitHub

### 1. Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `FastApiOrm`
3. Description: "A lightweight, production-ready ORM for FastAPI with async support"
4. Choose Public
5. Don't initialize with README (we already have one)
6. Click "Create repository"

### 2. Push Your Code

```bash
# Initialize git if not already done
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: FastAPI ORM v0.12.0 with composite keys support"

# Add remote repository
git remote add origin https://github.com/Alqudimi/FastApiOrm.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### 3. Create a Release on GitHub

1. Go to your repository on GitHub
2. Click "Releases" → "Create a new release"
3. Tag version: `v0.12.0`
4. Release title: `v0.12.0 - Composite Keys & Advanced Constraints`
5. Description: Copy from CHANGELOG_V0.12.md
6. Click "Publish release"

## Publishing to PyPI

### 1. Prepare Package

Ensure these files are ready:
- `setup.py` ✓
- `README_PYPI.md` ✓
- `LICENSE` ✓
- `requirements.txt` ✓
- `MANIFEST.in` ✓

### 2. Install Build Tools

```bash
pip install build twine
```

### 3. Build Package

```bash
# Clean previous builds
rm -rf dist/ build/ *.egg-info

# Build distribution packages
python -m build
```

This creates:
- `dist/fastapi-orm-0.12.0.tar.gz` (source distribution)
- `dist/fastapi_orm-0.12.0-py3-none-any.whl` (wheel)

### 4. Test on TestPyPI (Recommended)

```bash
# Register on TestPyPI first: https://test.pypi.org/account/register/

# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ fastapi-orm
```

### 5. Upload to PyPI

```bash
# Upload to PyPI
twine upload dist/*

# You'll be prompted for:
# Username: Alqudimi (or __token__ if using API token)
# Password: Your PyPI password or API token
```

### 6. Verify Installation

```bash
pip install fastapi-orm
```

## Post-Publishing

### Update Documentation

1. Add installation instructions to README:
   ```bash
   pip install fastapi-orm
   ```

2. Update version badges in README.md

### Announce Release

Consider announcing on:
- Twitter/X with #FastAPI #Python hashtags
- Reddit (r/Python, r/FastAPI)
- Dev.to or Medium blog post
- Python Discord servers
- Your personal blog

## Version Numbering

Follow Semantic Versioning (semver):
- `MAJOR.MINOR.PATCH`
- `0.12.0` → First release with composite keys
- `0.12.1` → Bug fix
- `0.13.0` → New features
- `1.0.0` → Stable release

## Future Releases

For subsequent releases:

1. Update version in `setup.py`
2. Create new CHANGELOG file
3. Build and test
4. Tag release in Git
5. Upload to PyPI
6. Create GitHub release

## Useful Commands

```bash
# Check package description
twine check dist/*

# View package contents
tar -tzf dist/fastapi-orm-0.12.0.tar.gz

# Install in development mode
pip install -e .

# Uninstall
pip uninstall fastapi-orm
```

## Troubleshooting

### Upload Fails

- Check version number isn't already used
- Verify PyPI credentials
- Ensure all required files are included

### Import Errors

- Check package structure
- Verify __init__.py files exist
- Test with `pip install -e .` locally

### Missing Files in Distribution

- Update MANIFEST.in
- Rebuild with `python -m build`
- Check with `tar -tzf dist/*.tar.gz`

## Resources

- PyPI Documentation: https://packaging.python.org/
- Twine Documentation: https://twine.readthedocs.io/
- Setuptools Documentation: https://setuptools.pypa.io/

## Contact

For publishing questions:
- Email: eng7mi@gmail.com
- GitHub: @Alqudimi

---

Good luck with your release! 🚀
