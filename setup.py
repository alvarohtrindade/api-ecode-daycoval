"""
Setup script para o pacote Daycoval API.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Ler README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding='utf-8') if readme_file.exists() else ""

# Ler requirements
requirements_file = Path(__file__).parent / "requirements.txt"
if requirements_file.exists():
    requirements = requirements_file.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]
else:
    requirements = [
        'requests>=2.25.0',
        'python-dotenv>=0.19.0',
        'mysql-connector-python>=8.0.0',
        'click>=8.0.0',
        'dataclasses;python_version<"3.7"'
    ]

setup(
    name="daycoval-api",
    version="2.0.0",
    author="Catalise Analytics",
    author_email="dev@catalise.com.br",
    description="Sistema limpo e modular para API Daycoval - Relatórios automatizados",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/catalise/daycoval-api",
    project_urls={
        "Bug Tracker": "https://github.com/catalise/daycoval-api/issues",
        "Documentation": "https://github.com/catalise/daycoval-api/wiki",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        'dev': [
            'pytest>=6.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'black>=22.0.0',
            'isort>=5.10.0',
            'flake8>=4.0.0',
            'mypy>=0.950',
        ],
        'docs': [
            'sphinx>=4.0.0',
            'sphinx-rtd-theme>=1.0.0',
            'myst-parser>=0.17.0',
        ],
        'test': [
            'pytest>=6.0',
            'pytest-asyncio>=0.21.0',
            'pytest-cov>=4.0.0',
            'responses>=0.20.0',
        ]
    },
    entry_points={
        'console_scripts': [
            'daycoval=daycoval.cli.main:main',
        ],
    },
    include_package_data=True,
    package_data={
        'daycoval': [
            'config/*.json',
            'data/*.json',
        ],
    },
    zip_safe=False,
    keywords=[
        'daycoval', 'api', 'financial', 'reports', 
        'automation', 'portfolios', 'funds'
    ],
)