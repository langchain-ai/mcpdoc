# Contributing to MCPDOC

Thank you for your interest in contributing to MCPDOC! This guide will help you get started with development.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- uv (Python package manager)

### Initial Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd mcpdoc
```

2. Install dependencies:
```bash
uv sync --all-groups
```

This will:
- Create a virtual environment in `.venv/`
- Install all runtime dependencies
- Install all test dependencies

3. Verify installation:
```bash
uv run python -c "import mcpdoc; print(mcpdoc.__version__)"
uv run mcpdoc --version
```

## Project Structure

```
mcpdoc/
├── mcpdoc/                 # Main package
│   ├── __init__.py        # Package initialization
│   ├── _version.py        # Version management
│   ├── cli.py             # Command-line interface
│   ├── main.py            # Core server logic
│   └── splash.py          # Startup banner
├── examples/              # Example implementations
│   └── langgraph.py       # Simple LangGraph server example
├── tests/                 # Test suite
│   └── unit_tests/        # Unit tests
├── pyproject.toml         # Project configuration
└── Makefile              # Common development tasks
```

## Development Workflow

### Making Changes

1. Create a new branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make your changes to the code

3. Format your code:
```bash
make format
# OR
uv run ruff format .
uv run ruff check --fix .
```

4. Check for linting issues:
```bash
make lint
# OR
uv run ruff check .
```

### Running Tests

Run tests before committing:

```bash
# Run all tests
make test
# OR
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/unit_tests/test_main.py

# Run with coverage
uv run pytest --cov=mcpdoc tests/
```

### Testing Your Changes Locally

Test the CLI with your changes:

```bash
# Using YAML config
uv run mcpdoc --yaml sample_config.yaml --transport sse --port 8082

# Using direct URLs
uv run mcpdoc --urls "LangGraph:https://langchain-ai.github.io/langgraph/llms.txt"
```

## Code Style Guidelines

### General Principles

1. Follow PEP 8 style guidelines
2. Use type hints for all function parameters and return values
3. Write clear docstrings for all public functions and classes
4. Keep functions focused and modular
5. Avoid code duplication - extract common patterns into helper functions

### Docstring Format

Use Google-style docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """Brief description of the function.

    Longer description if needed, explaining what the function does,
    any important details about its behavior, etc.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is empty
    """
    pass
```

### Type Hints

Always use type hints:

```python
from typing import List, Dict, Optional

def process_sources(
    sources: List[Dict[str, str]], 
    timeout: float = 10.0
) -> Optional[str]:
    """Process documentation sources."""
    pass
```

## Adding New Features

### Adding a New Tool to the MCP Server

1. Open `mcpdoc/main.py`
2. Add your tool function inside `create_server()`:

```python
@server.tool()
async def your_new_tool(param: str) -> str:
    """Description of your tool.
    
    Args:
        param: Description of parameter
        
    Returns:
        Description of return value
    """
    # Your implementation
    return result
```

3. Add tests in `tests/unit_tests/`
4. Update documentation

### Adding CLI Options

1. Open `mcpdoc/cli.py`
2. Add argument to `parse_args()`:

```python
parser.add_argument(
    "--your-option",
    type=str,
    help="Description of your option"
)
```

3. Use the option in `main()`:

```python
# In main() function
your_value = args.your_option
```

4. Update `EPILOG` with usage examples
5. Add tests

## Testing Guidelines

### Writing Tests

1. Create test files in `tests/unit_tests/`
2. Name test files as `test_<module_name>.py`
3. Name test functions as `test_<function_being_tested>`

Example test:

```python
import pytest
from mcpdoc.main import your_function

def test_your_function():
    """Test your_function with valid input."""
    result = your_function("input")
    assert result == "expected output"

def test_your_function_error():
    """Test your_function raises error for invalid input."""
    with pytest.raises(ValueError):
        your_function("")
```

### Test Categories

- **Unit tests**: Test individual functions (`tests/unit_tests/`)
- **Integration tests**: Test components working together (future)
- **End-to-end tests**: Test the full system (future)

## Common Tasks

### Adding a Dependency

```bash
# Add runtime dependency
uv add package-name

# Add development dependency
uv add --dev package-name

# Add to specific dependency group
# Edit pyproject.toml manually, then:
uv sync --all-groups
```

### Updating Dependencies

```bash
# Update all dependencies
uv sync --upgrade

# Update specific package
uv add package-name --upgrade
```

### Building the Package

```bash
# Build distribution files
uv build

# Install locally in editable mode
uv pip install -e .
```

## Pull Request Process

1. **Create a branch** from `main`
2. **Make your changes** following the guidelines above
3. **Add tests** for new functionality
4. **Run tests** and ensure they pass
5. **Format code** using `make format`
6. **Check for linting issues** using `make lint`
7. **Update documentation** as needed
8. **Commit changes** with clear, descriptive commit messages
9. **Push to your fork** and create a pull request
10. **Describe your changes** in the PR description

### Commit Message Guidelines

Use clear, descriptive commit messages:

```
Add new feature for X

- Implement function Y
- Add tests for Y
- Update documentation
```

Or for bug fixes:

```
Fix issue with domain validation

- Refactor domain checking logic
- Add test cases for edge cases
- Update error messages
```

## Areas for Contribution

### Easy Contributions

- Improve documentation
- Add more tests
- Fix typos or formatting
- Add examples

### Medium Contributions

- Add new CLI options
- Improve error messages
- Add configuration validation
- Optimize performance

### Advanced Contributions

- Add new transport protocols
- Implement caching
- Add authentication support
- Add plugin system

## Getting Help

- Read the [LEARNING_GUIDE.md](LEARNING_GUIDE.md) for understanding the codebase
- Check existing issues and pull requests
- Ask questions in discussions

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow the project's guidelines

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).

## Questions?

If you have questions about contributing, feel free to:
- Open an issue for discussion
- Ask in the project's discussion forum
- Reach out to the maintainers

Thank you for contributing to MCPDOC!

