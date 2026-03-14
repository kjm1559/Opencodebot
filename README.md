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
- `/restart` - Restart bot with git pull (clears all sessions)

### /compact Command

Two usage modes:

```
/compact              → Export current/auto-detected session
/compact <session_id> → Export specific session by ID
```

```

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
| `/restart` | Restart bot (git pull + restart) | `/restart` |

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

## Logging System

### Console Output (INFO only)
Terminal shows only INFO level and above:
- `INFO`, `WARNING`, `ERROR` visible
- `DEBUG` messages filtered out
- Format: `YYYY-MM-DD HH:MM:SS - LEVEL - message`

### File Logs (DEBUG+)
All debug information saved to rotating log files:
- **Location**: `src/opencode_bot/logs/`
- **Rotation**: Round-robin across 10 files (`app_0.log` ~ `app_9.log`)
- **Size Limit**: 10MB per file (auto-rotates when exceeded)
- **Format**: `YYYY-MM-DD HH:MM:SS - telegram_controller - LEVEL - message`
- **Index Tracking**: `.rotation_index` tracks current file

### Log File Management
```
src/opencode_bot/logs/
├── app_0.log         # Log file 0
├── app_1.log         # Log file 1
├── ...               # ...
├── app_9.log         # Log file 9
└── .rotation_index   # Current rotation index (0-9)
```
When `app_n.log` exceeds 10MB, contents move to `app_(n+1).log`.

## Session Auto-Extraction

Session IDs are automatically extracted from opencode output:
- `session_started` events captured
- Current session stored per user
- Available via `/current_session` command
