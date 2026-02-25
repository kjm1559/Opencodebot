# TELEGRAM CONTROLLER TEST PLAN
# TDD Approach

## Overview
This document provides a comprehensive test plan for the Telegram Controller using Test-Driven Development (TDD) principles, based on the specification in AGENTS.md.

## Test Plan Components

### 1. Core Functionality Tests

#### 1.1 process_output_line() Function Tests
- **Text Message Processing**: Validate that text messages are properly extracted
- **Tool Use Message Processing**: Validate that tool_use messages are properly formatted 
- **Step Filtering**: Validate that step_start and step_finish messages are filtered out
- **Error Handling**: Validate that malformed JSON is handled gracefully

#### 1.2 Session Management Tests
- **Session Storage**: Validate that chat/session mappings are stored/retreived correctly
- **Session Validation**: Validate the ability to validate session IDs against opencode session list
- **Session Format**: Validate that session lists are formatted properly for Telegram

#### 1.3 Command Execution Tests
- **Command Structure**: Validate that correct command arguments are constructed
- **Error Handling**: Validate that execution errors are reported properly

### 2. Command Handler Tests

#### 2.1 /session Command Handler
- **Valid Session List**: Test that valid session lists are returned 
- **Empty Session List**: Test that empty session lists are handled

#### 2.2 /set_session Command Handler
- **Valid Session ID**: Test that valid session IDs are accepted
- **Invalid Session ID**: Test that invalid session IDs are rejected

#### 2.3 /current_session Command Handler
- **Active Session**: Test that current session is returned when set
- **No Active Session**: Test that appropriate message is returned when no session set

#### 2.4 Regular Message Handler
- **With Session**: Test flow when session is set
- **Without Session**: Test flow when no session is set (should create new session)

### 3. Integration Tests

#### 3.1 Complete Flow Testing
- **End-to-end flow with session**
- **End-to-end flow without session**

### 4. Error Handling Tests
- **Invalid JSON input**
- **Subprocess execution failures** 
- **Telegram API failures**
- **Malformed command arguments**

### 5. Edge Case Tests
- **Empty messages**
- **Special characters in messages**
- **Large output processing**
- **Rate limiting scenarios**

## Implementation Approach

### Phase 1: Basic Components
1. Test `process_output_line()` function works correctly
2. Test session storage and retrieval functions
3. Test command construction for different scenarios

### Phase 2: Command Handler Testing
1. Test `/session` command handler behavior 
2. Test `/set_session` command handler behavior
3. Test `/current_session` command handler behavior

### Phase 3: Full Flow Testing  
1. Test complete message flow with existing session
2. Test complete message flow without session

### Phase 4: Edge Cases and Error Handling
1. Test error conditions
2. Test malformed inputs
3. Test boundary conditions

## Specific Test Cases

### Text Type Output Process
Input: `{"type":"text","text":"Hello World"}`
Expected: `"Hello World"`

### Tool Use Type Output Process
Input: `{"type":"tool_use","part":{"tool":"curl","state":{"input":{"url":"http://example.com"}}}}`
Expected: Formatted markdown output with tool name and input

### Step Filtering
Input: `{"type":"step_start","text":"Starting..."}`
Expected: `""` (empty string - filtered out)

### Session Storage
Operations: set/get current session ID
Expected: Session IDs stored/retrieved correctly per chat

### Complete Flow Test
1. No session set → command: `opencode run --continue`
2. Session set → command: `opencode run --session <id>`
3. Post-execution: Get latest session and set it as current

## Testing Framework Requirements

### Tools Needed:
- Python pytest framework
- unittest.mock for mocking external dependencies
- Coverage tools to ensure 90%+ test coverage

### Environment Requirements:
- Python 3.8 or higher
- opencode CLI installed and available in PATH
- TELEGRAM_BOT_TOKEN environment variable set
- Telegram bot tokens for integration testing (if needed)

## Test Coverage Goals

### Code Coverage:
- Target 90%+ line coverage
- All core functions should have tests
- Critical branches should be tested

### Functional Coverage:
- All commands from AGENTS.md should be tested
- All output filtering rules should be verified
- All session management should be tested
- Error scenarios should be covered

## Expected Test Results

Each test will validate:
1. Correctness of implementation vs specification
2. Edge case handling  
3. Error condition handling
4. Integration with external systems

## Risk Mitigation

### Potential Issues:
- Current implementation bugs in filtering logic
- External dependency failures (opencode CLI, Telegram API)
- Incomplete mock setups

### Mitigation:
- Start with basic unit tests
- Gradually add integration tests
- Ensure mocks are comprehensive