# Agent Rules for Telegram Controller

## Purpose

Rules and workflows for AI agent behavior when developing the Telegram Controller.

---

## Mandatory Workflow

**ALL modifications must follow this sequence:**

1. **ANALYZE** → Understand requirements, locate code, identify patterns
2. **PLAN** → Create detailed todo list
3. **IMPLEMENT** → Make changes, one logical unit at a time
4. **TEST** → Create/update test cases, run full suite
5. **DOCUMENT** → Update README.md if features changed
6. **COMMIT** → Atomic commits with meaningful messages
7. **PUSH** → Push to remote repository

**DEVIATION = INCOMPLETE WORK**

---

## Testing Requirements

### Mandatory Test Creation

**ALL code changes MUST include test cases:**

- **Location**: `tests/` folder
- **Coverage**: Every logical path, edge case, error condition
- **Types**: Unit tests, Integration tests, E2E tests

### Test Execution Protocol

**Before marking implementation complete:**

```bash
# Run full test suite
pytest tests/ -v

# Check coverage
pytest --cov=src --cov-report=term-missing
```

**Completion requirements:**
- ✅ All tests pass (exit code 0)
- ✅ No pre-existing tests broken
- ✅ New test files for new functionality
- ✅ Edge cases covered (errors, empty inputs, invalid data)

### Test Quality Standards

**Every test must:**
- Have descriptive name matching behavior
- Use `pytest` fixtures for setup/teardown
- Test failure conditions, not just happy paths
- Be deterministic (no flaky tests)

---

## Documentation Updates

### README.md Update Protocol

**Any feature modification REQUIRES README.md update:**

**When to update:**
- New command added
- Command behavior changed
- Usage patterns modified
- Configuration options added/removed

**What to update:**
- Command reference section
- Examples (current and testable)
- Message flow diagrams
- Feature list
- Usage instructions

### Commit Message Standards

**Format:**
```
<type>: <short description>
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Test addition/fix
- `refactor:` Code restructuring
- `chore:` Maintenance tasks

**Requirements:**
- Short summary (≤50 chars)
- Imperative tense ("Add" not "Added")

---

## Development Rules

### Code Quality

1. **Type Safety**: No `as any`, `@ts-ignore`, or type suppression
2. **Error Handling**: All `try/except` blocks must log with context
3. **Code Patterns**: Single-purpose functions (<50 lines), follow existing style

### Git Workflow

1. **Atomic Commits**: One logical change per commit, include tests
2. **Push Protocol**: Verify changes first, keep remote updated
3. **Branch Safety**: Never force push to `main`

### Telegram-Specific Rules

1. **MarkdownV2 Safety**: ALL user-facing text MUST be escaped with `escape_markdown_v2()`
2. **Error Recovery**: Graceful degradation, rate limit awareness
3. **User Experience**: Typing indicator for long operations

---

## Verification Checklist

**Before marking task COMPLETE:**

- [ ] Code implements requested feature
- [ ] Test cases created in `tests/`
- [ ] All tests pass (`pytest tests/ -v`)
- [ ] README.md updated if feature changed
- [ ] Code follows existing patterns
- [ ] Error handling implemented
- [ ] Telegram messages properly escaped
- [ ] Commit message is clear and descriptive
- [ ] Changes pushed to remote

**MISSING ANY ITEM = TASK INCOMPLETE**

---

## Project Context

### Overview
Telegram bot controlling `opencode` via CLI commands with real-time updates and session management.

### Core Features

**Real-Time Updates**:
- Typing indicator during execution
- Action streams (Reading, Modifying, Running, Fetching, Searching)
- Session tracking and error notifications

**Session Management**:
- List/Set/Create/Export/Reset sessions

**Commands**:
- `/session`, `/set_session`, `/current_session`, `/new_session`
- `/compact`, `/reset`, `/project`, `/workspace`, `/model`

**Logging**:
- Console: INFO+ only
- Files: DEBUG+ with round-robin rotation (10 files × 10MB)