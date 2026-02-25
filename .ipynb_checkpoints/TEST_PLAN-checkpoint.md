# Telegram Controller - TDD Test Plan

## Overview
This document outlines a Test-Driven Development (TDD) approach for testing the Telegram Controller that manages OpenCode sessions via Telegram commands.

## Test Structure

### 1. Core Function Tests
- `process_output_line()` - Handles various opencode output types
- `format_message()` - Formats structured messages for Telegram
- `stream_opencode_output()` - Streams command output to Telegram
- `run_opencode_command()` - Executes opencode commands

### 2. Session Management Tests
- `set_current_session_id()` / `get_current_session_id()` - Session storage
- `is_valid_session_id()` - Session validation
- `format_session_list()` - Session list formatting

### 3. Command Handler Tests
- `/session` command handler
- `/set_session` command handler
- `/current_session` command handler
- Regular message handler flow

### 4. Integration Tests
- Complete message flow with existing session
- Complete message flow without session
- Error handling scenarios

## Detailed Test Cases

### 1. Text Type Handling
**Test Case:** process_output_line with text message
- Input: `{"type":"text","text":"Hello World"}`
- Expected: "Hello World"

**Test Case:** process_output_line with nested text
- Input: `{"type":"text","part":{"text":"Nested text"}}`
- Expected: "Nested text"

### 2. Tool Use Type Handling
**Test Case:** process_output_line with tool_use message
- Input: `{"type":"tool_use","part":{"tool":"example_tool","state":{"status":"success","input":{"param1":"value1"}}}}`
- Expected: Formatted markdown with tool name, status, and input JSON

### 3. Filtering Tests
**Test Case:** Filtering step_start messages
- Input: `{"type":"step_start","text":"Starting..."}`
- Expected: Empty string (filtered out)

**Test Case:** Filtering step_finish messages
- Input: `{"type":"step_finish","text":"Finished"}`
- Expected: Empty string (filtered out)

### 4. Session Management Tests
**Test Case:** Setting session ID
- Input: chat_id="test123", session_id="sess_456"
- Expected: Session is stored and retrievable

**Test Case:** Getting session ID
- Input: chat_id="test123"
- Expected: Returns correct session ID or None

**Test Case:** Session validation
- Input: valid session ID, chat_id
- Expected: Returns True

**Test Case:** Invalid session validation
- Input: invalid session ID, chat_id
- Expected: Returns False

### 5. Command Handler Tests
**Test Case:** `/session` command
- Input: /session command message
- Expected: Calls `opencode session list` and formats response

**Test Case:** `/set_session` command
- Input: /set_session sess_123
- Expected: Sets session ID and replies appropriately

**Test Case:** `/current_session` command
- Input: /current_session command message
- Expected: Returns current session ID or "No active session"

**Test Case:** Regular message flow no session
- Input: Text message with no active session
- Expected: Executes `opencode run --continue`, gets session list, sets latest as current

**Test Case:** Regular message flow with session
- Input: Text message with active session
- Expected: Executes `opencode run --session <id>`

## Test Coverage Matrix

| Feature | Unit Test | Integration Test | Functional Test |
|---------|-----------|------------------|-----------------|
| Text processing | ✓ |  |  |
| Tool use processing | ✓ |  |  |
| Filtering | ✓ |  |  |
| Session storage | ✓ |  |  |
| Session validation | ✓ |  |  |
| Command execution | ✓ |  |  |
| /session command | ✓ |  |  |
| /set_session command | ✓ |  |  |
| /current_session command | ✓ |  |  |
| Regular message flow | ✓ | ✓ | ✓ |
| Error handling | ✓ | ✓ | ✓ |

## Test Execution Requirements

1. All tests must run successfully in TDD style (write test → make it pass → refactor)
2. Mock external systems (Telegram API, subprocess) 
3. Test edge cases (empty input, malformed JSON, invalid sessions)
4. Verify message formatting according to AGENTS.md specifications
5. Validate command arguments construction matches specification

## Quality Metrics

- Code coverage: 90%+ for core functionality
- All JSON parsing errors handled gracefully
- No external dependencies required for test execution
- Tests should be runnable in any environment
- Test cases should match the exact specifications in AGENTS.md