# Contributing to DCSS Bot

Thank you for your interest in contributing to the DCSS Bot project! This document provides guidelines for contributions.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. **Check existing issues** - See if your issue has already been reported
2. **Create a new issue** - Include:
   - Clear description of the problem
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Any relevant logs from `logs/` directory
   - Your system info (OS, Python version, etc.)

### Submitting Code Changes

1. **Fork the repository** and create a feature branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code style (see below)

3. **Test your changes**:
   ```bash
   # Run the test suite
   bash run_tests.sh
   
   # All tests must pass before submitting
   ```

4. **Update documentation**:
   - Update relevant `.md` files
   - Add entries to `CHANGELOG.md` under "Unreleased" section
   - Update docstrings in code

5. **Commit with clear messages**:
   ```bash
   git commit -m "Brief summary of changes"
   git commit -m "
   - More detailed explanation of changes
   - Include reasoning if not obvious
   - Reference any related issues (#123)
   "
   ```

6. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style

### Python Code

- Follow **PEP 8** conventions
- Use **type hints** for function parameters and returns
- Add **docstrings** to classes and public methods
- Use descriptive variable names

Example:
```python
def extract_health(output: str) -> tuple[int, int]:
    """
    Extract health from game output.
    
    Args:
        output: Raw game output containing health status
        
    Returns:
        Tuple of (current_health, max_health)
    """
    # implementation...
```

### Documentation

- Use **Markdown** for all documentation
- Keep lines under 100 characters where practical
- Use clear, concise language
- Include code examples for complex features

### Commit Messages

- Start with a clear, short summary (50 chars or less)
- Leave a blank line, then detailed explanation if needed
- Reference issues with `#123` format
- Explain *what* changed and *why* (not just *how*)

## Architecture Guidelines

When adding features, keep these principles in mind:

### Pyte Buffer as Primary Source

All game state decisions MUST use the pyte buffer (via `screen_buffer.get_screen_text()`), not raw PTY output. Raw output contains only ANSI code deltas and is incomplete.

**Correct:**
```python
screen_text = self.screen_buffer.get_screen_text()
enemy_detected, name = self._detect_enemy_in_range(screen_text)
```

**Incorrect:**
```python
enemy_detected, name = self._detect_enemy_in_range(self.last_screen)  # Raw output!
```

### Activity Logging

Log important bot actions using the activity panel:
```python
self._log_activity("Detected enemy: dragon", level="warning")
```

Levels: `"success"`, `"info"`, `"warning"`, `"error"`, `"debug"`

### Game State Decisions

Place decision logic in `_decide_action()` method. Key decision points:

1. **Level-up messages** - Check early, handle state transitions
2. **Enemy detection** - Check TUI monsters section
3. **Health-based actions** - Read from TUI status line
4. **Exploration** - Use auto-explore ('o') or manual movement
5. **Game over** - Detect and handle gracefully

## Testing

### Running Tests

```bash
# Run all tests
bash run_tests.sh

# Run specific test file
pytest tests/test_bot.py -v

# Run specific test
pytest tests/test_bot.py::test_character_creation_flow -v

# Run with coverage
pytest --cov=. tests/
```

### Writing Tests

- Create test files in `tests/` directory
- Use pytest conventions
- Mock external dependencies (game state, output)
- Test both happy path and error cases

Example:
```python
def test_enemy_detection(game_state_parser):
    """Test that enemies are detected from TUI output."""
    output = "S   ball python"
    enemy_detected, name = parser._detect_enemy_in_range(output)
    
    assert enemy_detected is True
    assert name == "ball python"
```

## Documentation Files

When making significant changes, update the relevant documentation:

- **README.md** - User-facing features and usage
- **ARCHITECTURE.md** - Technical design and components
- **DEVELOPER_GUIDE.md** - Implementation details and patterns
- **CHANGELOG.md** - Detailed changes with version numbers
- **Specific guides** - If adding major features (create new `.md` file)

## Review Process

Once you submit a PR:

1. Automated tests will run - all must pass
2. Code review will provide feedback
3. Make requested changes in additional commits
4. Once approved, your changes will be merged!

## Questions?

If you have questions:
1. Check the existing documentation in `/docs` and `*.md` files
2. Review the [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) for implementation details
3. Look at recent PRs and issues for examples

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for helping make DCSS Bot better! 🎉
