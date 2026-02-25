# Telegram Controller for OpenCode

## Overview
Telegram bot controlling `opencode` via CLI commands with intelligent typing indicators and session management.

## Core Features
- **Session Management**: Create, list, set, and reset sessions
- **Command Execution**: Run opencode commands with real-time streaming output  
- **Typing Indicators**: Intelligent typing action control
- **Error Handling**: Comprehensive error reporting

## Commands
- `/session` - List available sessions
- `/set_session <id>` - Set current session
- `/current_session` - Show current session
- `/new_session` - Create new session  
- `/compact <session_id>` - Compact current session
- `/reset` - Clear current session

## Typing Control
- Typing indicators sent only at command start
- Remains active until command completion
- "Command completed successfully" signals typing indicator removal

## Implementation
- Uses JSON formatting for all opencode commands
- Filters out `step_start`/`step_finish` messages
- Streams output to Telegram in real-time
- Supports large outputs with proper error handling