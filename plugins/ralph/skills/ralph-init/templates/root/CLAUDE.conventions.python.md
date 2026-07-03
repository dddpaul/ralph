Use uv exclusively for Python package management in this project.

**Package Management Commands**

- All Python dependencies **must be installed, synchronized, and locked** using uv
- Never use pip, pip-tools, poetry, or conda directly for dependency management

Use these commands:

- Install dependencies: `uv add <package>`
- Remove dependencies: `uv remove <package>`
- Sync dependencies: `uv sync`

**Running Python Code**

- Run a Python script with `uv run <script-name>.py`
- Run Python tools like Pytest with `uv run pytest` or `uv run ruff`
- Launch a Python repl with `uv run python`
- Run test with `uv run pytest <test-name>.py`

**Managing Scripts with PEP 723 Inline Metadata**

- Run a Python script with inline metadata (dependencies defined at the top of the file) with: `uv run script.py`
- You can add or remove dependencies manually from the `dependencies =` section at the top of the script, or
- Or using uv CLI:
    - `uv add package-name --script script.py`
    - `uv remove package-name --script script.py`

### Code Style

- Formatting: Follow PEP 8, use ruff formatter
- Imports: Sort imports with standard library first, then third-party, then local
- Types: Use type hints for all functions and methods
- Naming: snake_case for functions/variables, PascalCase for classes
- Error handling: Use specific exceptions, include context in error messages
- Docstrings: Google-style docstrings for public functions/classes
- Line length: Maximum 88 characters
- Function length: Keep functions focused and under 50 lines
