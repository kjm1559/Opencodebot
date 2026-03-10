# Agent Rules for Telegram Controller

## Purpose

Rules and workflows governing AI agent behavior when developing the Telegram Controller for OpenCode.

---

## Core Principles

**MANDATORY WORKFLOW** - All modifications must follow this sequence:

1. **ANALYZE** → Understand requirements, locate relevant code, identify patterns
2. **PLAN** → Create detailed todo list, outline implementation steps
3. **IMPLEMENT** → Make changes, one logical unit at a time
4. **TEST** → Create/update test cases, run full test suite
5. **DOCUMENT** → Update README.md if behavior/features changed
6. **COMMIT** → Atomic commits with meaningful messages
7. **PUSH** → Push to remote repository

**DEVIATION FROM THIS FLOW = INCOMPLETE WORK**

---

## Testing Requirements

### Mandatory Test Creation

**ALL code changes MUST include corresponding test cases:**

1. **Location**: `tests/` folder hierarchy
2. **Coverage**: Every logical path, edge case, and error condition
3. **Types**:
   - **Unit tests**: Individual functions/components
   - **Integration tests**: Multi-component interactions
   - **E2E tests**: Full workflow validation

### Test Execution Protocol

Before marking ANY implementation as complete:

```
1. Run full test suite: `pytest tests/ -v`
2. Verify ALL tests pass (exit code 0)
3. Check coverage: `pytest --cov=src --cov-report=term-missing`
4. Ensure NO regression in existing tests
```

**Evidence of completion MUST include**:
- ✅ Test output logs showing 100% pass rate
- ✅ No pre-existing tests broken
- ✅ New test files created for new functionality
- ✅ Edge cases covered (error handling, empty inputs, invalid data)

### Test Quality Standards

**Every test case must**:
- Have descriptive name matching tested behavior
- Use `pytest` fixtures for setup/teardown
- Test failure conditions, not just happy paths
- Be deterministic (no flaky tests)
- Include assertions that verify actual behavior

---

## Documentation Updates

### README.md Update Protocol

**Any feature modification or addition REQUIRES README.md update:**

1. **When to update**:
   - New command added
   - Command behavior changed
   - Usage patterns modified
   - Configuration options added/removed
   - Message flow changed

2. **What to update**:
   - Command reference section
   - Examples (must be current and testable)
   - Message flow diagrams
   - Feature list
   - Usage instructions

3. **Verification**:
   - README.md examples MUST match actual code behavior
   - All commands listed must be documented
   - Screenshots/diagrams updated if visual flow changed

### Commit Message Standards

**Format:**
```
<type>: <short description>

<optional: detailed explanation>
- Bullet points for changes
- Impact summary
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Test addition/fix
- `refactor:` Code restructuring
- `chore:` Maintenance tasks

**MANDATORY ELEMENTS:**
- Short summary (50 chars or less)
- Imperative tense ("Add feature" not "Added feature")
- Reference issue number if applicable

---

## General Development Rules

### Code Quality

1. **Type Safety**:
   - NEVER use `as any`, `@ts-ignore`, type suppression
   - All functions must have proper type hints
   - Never suppress type errors without commented justification

2. **Error Handling**:
   - All `try/except` blocks must log errors with context
   - User-facing error messages must be in Telegram-friendly format
   - Never use empty `except:` or `pass` in catch blocks

3. **Code Patterns**:
   - Follow existing codebase style (consistent indentation, naming)
   - Functions should be single-purpose (< 50 lines ideally)
   - Extract repeated logic into helper functions

### Git Workflow

1. **Atomic Commits**:
   - One logical change per commit
   - All related tests included in same commit
   - README.md updates in same commit as feature

2. **Push Protocol**:
   - ALWAYS verify changes before pushing
   - Check commit message clarity
   - Ensure remote branch is up-to-date first

3. **Branch Safety**:
   - NEVER force push to `main` without explicit request
   - NEVER amend already pushed commits
   - Keep `main` branch in working state always

### Telegram-Specific Rules

1. **MarkdownV2 Safety**:
   - ALL user-facing text MUST be escaped with `escape_markdown_v2()`
   - Special characters that require escaping: `_ * [ ] ( ) ~ ` > # + - = | { } . !`
   - Test messages before production deployment

2. **Error Recovery**:
   - Failed messages should include fallback options
   - Graceful degradation (bot stays responsive after errors)
   - Rate limit awareness (Telegram API limits)

3. **User Experience**:
   - Typing indicator for long operations
   - Progress updates for multi-step actions
   - Clear error messages in user's language

---

## Verification Checklist

**Before marking ANY task COMPLETE**:

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

## Project Context (Reference)

### Telegram Controller Overview

Telegram bot controlling `opencode` via CLI commands with real-time updates and session management.

### Core Features

**Real-Time Updates**:
- Typing Indicator during command execution
- Action Streams (📖 Reading, ✏️ Modifying, 💻 Running, 🌐 Fetching, 🔍 Searching)
- Session Tracking (automatic session ID extraction)
- Error Notifications

**Session Management**:
- List/Set/Create/Export sessions
- Reset sessions

**Commands**:
- `/session`, `/set_session`, `/current_session`, `/new_session`
- `/compact`, `/reset`, `/project`, `/workspace`, `/model`