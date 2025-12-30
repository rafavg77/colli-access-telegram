# Copilot Instructions for colli-access-telegram

## Project Overview
This is a Telegram bot client for the colli-access-backend API. The project is written in Python and provides a Telegram interface for interacting with the backend service.

## Code Style and Conventions
- **Language**: Python
- **Code Style**: Follow PEP 8 style guidelines
- **Type Hints**: Use Python type hints for function signatures and variables where appropriate
- **Docstrings**: Use clear and concise docstrings for modules, classes, and functions
- **Imports**: Group imports in the following order:
  1. Standard library imports
  2. Related third-party imports
  3. Local application/library specific imports

## Build and Test Process
- **Build**: This is a Python project. Ensure dependencies are installed before running or testing
  - Use `pip install -r requirements.txt` if a requirements file exists
  - Or use the project's dependency manager (poetry, pipenv, etc.) as specified in the project
- **Testing**: Run tests using the project's testing framework (pytest, unittest, etc.)
  - Check for test files in `tests/` or `test_*.py` files
  - Run with appropriate test commands as defined in the project
- **Linting**: Use standard Python linting tools
  - Check if the project uses ruff, flake8, pylint, or similar
  - Configuration may be in `pyproject.toml`, `setup.cfg`, or dedicated config files

## Validation Steps
1. **Code Review**: Ensure all changes follow the project's code style
2. **Type Checking**: Run type checkers if the project uses them (mypy, pyright, etc.)
3. **Linting**: Run linters to catch style and potential issues
4. **Testing**: Run the test suite to ensure no regressions
5. **Security**: Check for security vulnerabilities, especially:
   - Never commit API tokens, secrets, or credentials
   - Validate and sanitize user input from Telegram messages
   - Follow secure coding practices for API interactions

## Security and Compliance
- **Secrets Management**: Never hardcode API keys, bot tokens, or credentials
  - Use environment variables or secure secret management
  - Ensure `.env` files are in `.gitignore`
- **API Security**: When interacting with the backend API:
  - Validate all inputs
  - Use HTTPS for API calls
  - Handle authentication tokens securely
- **User Data**: Handle Telegram user data responsibly
  - Follow privacy best practices
  - Don't log sensitive user information

## Telegram Bot Specific Guidelines
- **Bot Token**: Store the Telegram bot token securely using environment variables
- **Error Handling**: Implement proper error handling for:
  - Network failures
  - API rate limits
  - Invalid user inputs
- **User Experience**: Provide clear and helpful messages to users
- **Async Operations**: Use async/await patterns for Telegram bot operations when applicable

## Dependencies
- Review and approve any new dependencies before adding them
- Keep dependencies up to date for security patches
- Document the purpose of new dependencies

## Documentation
- Update README.md when adding new features or changing functionality
- Document API endpoints and their usage
- Provide examples for common use cases
