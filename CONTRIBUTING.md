# Contributing to Ticket System

Thank you for your interest in contributing to the Ticket System! This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)
- [Pull Request Process](#pull-request-process)
- [Testing](#testing)
- [Documentation](#documentation)

## 🤝 Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment for all contributors.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/TicketSystem.git
   cd TicketSystem
   ```
3. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
5. **Set up the database**:
   ```bash
   python manage.py migrate
   ```

## 💻 Development Process

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**:
   - Write clean, readable code
   - Follow the project's coding standards
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   pytest
   pytest --cov=ticket_system  # With coverage
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "Add your descriptive commit message"
   ```

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request** on GitHub

## 📝 Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Maximum line length: 88 characters (Black formatter default)
- Use type hints where appropriate

### Code Formatting

We use the following tools for code quality:

```bash
# Format code with Black
black ticket_system/

# Sort imports with isort
isort ticket_system/

# Lint with flake8
flake8 ticket_system/

# Type checking with mypy
mypy ticket_system/
```

### Django Best Practices

- Keep views thin, use services for business logic
- Use Django ORM efficiently, avoid N+1 queries
- Follow Django's security best practices
- Use proper error handling and logging

## 📝 Commit Messages

Write clear and descriptive commit messages:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples

```
feat(tickets): Add bulk ticket assignment feature

Implement functionality to assign multiple tickets to a user at once.
This improves efficiency for administrators managing large ticket volumes.

Closes #123
```

```
fix(auth): Resolve JWT token expiration issue

Fixed bug where tokens were expiring earlier than expected due to
timezone inconsistency.

Fixes #456
```

## 🔄 Pull Request Process

1. **Update Documentation**: Ensure all relevant documentation is updated
2. **Add Tests**: Include tests for new features or bug fixes
3. **Update CHANGELOG**: Add an entry describing your changes
4. **Ensure CI Passes**: All tests and checks must pass
5. **Request Review**: Tag relevant maintainers for review
6. **Address Feedback**: Respond to review comments promptly

### PR Checklist

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated and passing
- [ ] No new warnings generated
- [ ] Dependent changes merged and published

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=ticket_system --cov-report=html

# Run specific test file
pytest tests/test_models.py

# Run tests matching a pattern
pytest -k "test_ticket"
```

### Writing Tests

- Write unit tests for all new functionality
- Aim for >80% code coverage
- Use Django's `TestCase` or pytest fixtures
- Mock external services and APIs
- Test both success and failure cases

### Test Structure

```python
def test_feature_name():
    """Test description of what is being tested."""
    # Arrange: Set up test data

    # Act: Execute the code being tested

    # Assert: Verify the results
    pass
```

## 📚 Documentation

### Code Documentation

- Add docstrings to all public functions, classes, and modules
- Use Google-style or NumPy-style docstrings
- Include parameter types and return types
- Provide usage examples for complex functionality

### Example

```python
def create_ticket(title: str, description: str, user: User) -> Ticket:
    """
    Create a new support ticket.

    Args:
        title: The ticket title
        description: Detailed description of the issue
        user: The user creating the ticket

    Returns:
        The newly created Ticket instance

    Raises:
        ValidationError: If title or description is empty
    """
    pass
```

## 🐛 Reporting Bugs

When reporting bugs, please include:

- Clear description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details (OS, Python version, etc.)
- Screenshots or logs if applicable

## 💡 Suggesting Features

Feature requests are welcome! Please include:

- Clear description of the feature
- Use case and benefits
- Possible implementation approach
- Any relevant examples or mockups

## 📞 Questions?

If you have questions about contributing, feel free to:

- Open an issue for discussion
- Contact the maintainers

---

Thank you for contributing to Ticket System! 🎉
