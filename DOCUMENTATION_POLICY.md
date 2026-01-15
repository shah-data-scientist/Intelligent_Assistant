# Documentation Policy

This project follows the global documentation policy defined in:
`C:\Users\shahu\Documents\coding_agent_policies\GLOBAL_POLICY.md`

## Quick Reference

### Code Changes = Documentation Changes

When modifying code, you MUST update:
- Inline docstrings
- Type hints
- External documentation (.md files)
- README if user-facing changes
- Examples if affected

### Commit Checklist

Before committing:
- [ ] Code changes complete
- [ ] Docstrings updated
- [ ] External docs updated
- [ ] README updated (if needed)
- [ ] Tests passing
- [ ] Linting passing

## Standards

### Python Docstrings

```python
def function_name(param: str) -> int:
    """Brief one-line description.

    Longer description if needed explaining the purpose,
    behavior, and any important details.

    Args:
        param: Description of parameter

    Returns:
        Description of return value

    Raises:
        ValueError: When and why this is raised
    """
    pass
```

### Type Hints

Always use Python 3.10+ style type hints:
```python
# ✓ Correct
def process(items: list[dict[str, int]]) -> tuple[int, int]:
    pass

# ✗ Incorrect (old style)
from typing import List, Dict, Tuple
def process(items: List[Dict[str, int]]) -> Tuple[int, int]:
    pass
```

## Full Policy

For complete documentation standards, auditing procedures, and requirements verification, refer to the global policy file.
