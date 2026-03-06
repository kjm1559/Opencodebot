# Telegram Controller for OpenCode

## Overview
Telegram bot controlling `opencode` via CLI commands with real-time updates and session management.

## Core Features

### Real-Time Updates
- **Typing Indicator**: Shows typing status during command execution
- **Action Streams**: Real-time tool usage notifications with file/path details
  - 📖 Reading: src/telegram_controller.py
  - ✏️ Modifying: README.md
  - 💻 Running: git status
  - 🌐 Fetching: https://example.com
  - 🔍 Searching: **/*.py
- **Session Tracking**: Automatic session ID extraction and display
- **Error Notifications**: Immediate error alerts during execution

### Session Management
- List available sessions
- Set/create current session
- Compact sessions
- Reset sessions

### Output Streaming
- Minimal real-time updates (action messages only)
- Comprehensive summary at completion
- Full details in chunks (if available)

## Commands
- `/session` - List available sessions
- `/set_session <id>` - Set current session
- `/current_session` - Show current session
- `/new_session` - Create new session  
- `/compact <session_id>` - Compact session
- `/reset` - Clear current session

## Implementation Details
- **JSON Format**: All opencode commands use `--format json`
- **Filtering**: Step start/finish messages filtered for cleaner output
- **Truncation**: Long values truncated to 150 chars with "..."
- **Deduplication**: Duplicate action messages suppressed
- **Error Handling**: Graceful error recovery for Telegram messages
- **Logging**: DEBUG level logging to terminal (with timestamps)

## Message Flow
```
[User command]
  ↓
🔄 Typing indicator started
  ↓
📖 Reading: src/file.py (real-time action)
✏️ Modifying: README.md
💻 Running: git status
  ↓
⚠️ Error: <optional error message>
  ↓
📊 Summary (with activity stats)
📋 Full Details (chunked if long)
  ↓
✅ Completed (typing stops)
```

## Session Auto-Extraction
Sessions IDs are automatically extracted from opencode output:
- `session_started` events captured
- Current session stored per user
- Available via `/current_session` command