# Contributing to FalconEye

Thank you for your interest in contributing to FalconEye! This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](https://github.com/Vivek9454/FalconEye/issues)
2. If not, create a new issue using the [Bug Report template](.github/ISSUE_TEMPLATE/bug_report.md)
3. Include:
   - Clear description of the bug
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python version, device)

### Suggesting Features

1. Check if the feature has been requested in [Issues](https://github.com/Vivek9454/FalconEye/issues)
2. Create a new issue using the [Feature Request template](.github/ISSUE_TEMPLATE/feature_request.md)
3. Describe the feature, its use case, and potential implementation

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass (`pytest tests/`)
6. Update documentation if needed
7. Commit with clear messages
8. Push to your fork (`git push origin feature/amazing-feature`)
9. Open a Pull Request using the [PR template](.github/pull_request_template.md)

## Development Setup

1. Clone your fork:
   ```bash
   git clone https://github.com/YOUR_USERNAME/FalconEye.git
   cd FalconEye
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   pip install pytest pytest-cov  # For testing
   ```

4. Set up environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your test credentials
   ```

5. Run tests:
   ```bash
   pytest tests/ -v
   ```

## Code Style

- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and small
- Add comments for complex logic

## Commit Messages

Use clear, descriptive commit messages:

```
feat: Add face recognition caching
fix: Resolve memory leak in video processing
docs: Update installation instructions
test: Add tests for authentication endpoints
refactor: Simplify camera connection logic
```

## Testing

- Write tests for new features
- Ensure existing tests pass
- Aim for meaningful test coverage
- Test edge cases and error conditions

## Documentation

- Update README.md for user-facing changes
- Update API documentation for endpoint changes
- Add docstrings to new functions/classes
- Update CHANGELOG.md for significant changes

## Security

- Never commit secrets or credentials
- Use environment variables for configuration
- Follow security best practices in SECURITY.md
- Report security vulnerabilities privately

## Questions?

Feel free to open an issue for questions or reach out to maintainers.

Thank you for contributing to FalconEye!

