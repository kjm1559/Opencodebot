# Telegram Controller for OpenCode

Telegram bot controlling `opencode` via CLI commands with real-time updates and session management.

## Features

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
- Export sessions (backup)
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
- `/compact <session_id>` - Export session (backup)
- `/reset` - Clear current session

### /compact Command

Two usage modes:

```
/compact              → Export current/auto-detected session
/compact <session_id> → Export specific session by ID
```

Example:
```
/compact ses_3371a7af2ffe0ncZGUfrsaVMeJ
```

### Quick Start

## Quick Start

```bash
# Start the Telegram bot
python src/opencode_bot/telegram_controller.py
```

## Telegram Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/session` | List all available sessions | `/session` |
| `/current_session` | Show current session ID | `/current_session` |
| `/set_session <id>` | Set specific session | `/set_session ses_abc123` |
| `/new_session` | Create new session | `/new_session` |
| `/compact <session_id>` | Export session data | `/compact ses_abc123` |
| `/reset` | Clear current session | `/reset` |

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

## Implementation Details

- **JSON Format**: All opencode commands use `--format json`
- **Filtering**: Step start/finish messages filtered for cleaner output
- **Truncation**: Long values truncated to 150 chars with "..."
- **Deduplication**: Duplicate action messages suppressed
- **Error Handling**: Graceful error recovery for Telegram messages
- **Logging**: DEBUG level logging to terminal (with timestamps)

## Session Auto-Extraction

Session IDs are automatically extracted from opencode output:
- `session_started` events captured
- Current session stored per user
- Available via `/current_session` command
