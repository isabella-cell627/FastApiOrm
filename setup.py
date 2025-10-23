from setuptools import setup, find_packages

with open("README_PYPI.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="fastapi-orm",
    version="0.11.0",
    author="Abdulaziz Al-Qadimi",
    author_email="eng7mi@gmail.com",
    description="A production-ready ORM for FastAPI with async support, automatic Pydantic integration, and Django-like syntax",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Alqudimi/FastApiOrm",
    project_urls={
        "Bug Tracker": "https://github.com/Alqudimi/FastApiOrm/issues",
        "Documentation": "https://github.com/Alqudimi/FastApiOrm/tree/main/doc",
        "Source Code": "https://github.com/Alqudimi/FastApiOrm",
        "Changelog": "https://github.com/Alqudimi/FastApiOrm/blob/main/CHANGELOG_V0.11.md",
    },
    packages=find_packages(exclude=["tests", "examples", "*.tests", "*.tests.*", "docs", ".local", "attached_assets"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Database",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Framework :: AsyncIO",
        "Operating System :: OS Independent",
        "Typing :: Typed",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    extras_require={
        "redis": ["redis>=5.0.0"],
        "websockets": ["websockets>=12.0"],
        "graphql": ["strawberry-graphql>=0.200.0"],
        "files": ["aiofiles>=23.0.0", "boto3>=1.28.0", "pillow>=10.0.0"],
        "dev": ["pytest>=7.4.0", "pytest-asyncio>=0.21.0", "httpx>=0.24.0"],
        "all": [
            "redis>=5.0.0",
            "websockets>=12.0",
            "strawberry-graphql>=0.200.0",
            "aiofiles>=23.0.0",
            "boto3>=1.28.0",
            "pillow>=10.0.0",
        ],
    },
    keywords=[
        "fastapi",
        "orm",
        "sqlalchemy",
        "async",
        "pydantic",
        "database",
        "postgresql",
        "mysql",
        "sqlite",
        "rest-api",
        "crud",
        "asyncio",
        "multi-tenancy",
        "audit-logging",
        "caching",
        "websockets",
    ],
    include_package_data=True,
    package_data={
        "fastapi_orm": ["py.typed"],
    },
    zip_safe=False,
)
