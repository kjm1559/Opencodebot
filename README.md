# OpenCode Telegram Controller

A Telegram bot that controls the OpenCode CLI via Telegram commands with real-time updates and session management.

## Features

- **Real-time Streaming**: All tool executions shown immediately (no deduplication)
- **Input Details Display**: Shows full command parameters in separate messages
- **Smart Truncation**: 100 char preview with "...", long inputs in separate messages
- **Typing Indicators**: Shows typing status during command execution
- **Summary Mode**: Clean emoji-based summary with detailed breakdown
- **Logs to Terminal**: Full DEBUG-level command output to terminal
- **Project Management**: List, switch, and clone projects with session awareness
- **Session Management**: Create, list, set, and reset sessions
- **Session Auto-Detection**: `/current_session` and `/compact` auto-find latest session
- **Model Management**: List and set AI models from opencode
- **Status Monitoring**: View current model, project, and session status
- **Usage Statistics**: Track opencode usage with detailed statistics
- **Session History**: View and manage recent sessions
- **Command Cancellation**: Cancel running commands
- **Bot Restart**: `/restart` command to restart the bot with startup notification
- **Startup Notification**: Sends "Bot started!" message on launch (if `TELEGRAM_CHAT_ID` set)
- **Error Handling**: Comprehensive error reporting and logging

## Commands

### Monitoring & Control
- `/status` - Show current status (model, project, session)
- `/stats` - Show opencode usage statistics
- `/history` - Show recent session history (last 10)
- `/cancel` - Cancel currently running command

### Model Management
- `/model` - List available models and show current model
- `/model <model_name>` - Set current model (e.g., `/model ollama/qwen3.5:27b`)

### Project Management
- `/project` - List all projects in `~/projects/`
- `/project <number>` - Switch to project by number (keeps existing session)
- `/project <project-name>` - Switch to project by name (keeps existing session)
- `/project <git-url>` - Clone new project from git URL (creates new session)

**Examples:**
```bash
/project              # List all projects
/project 1            # Switch to first project (session preserved)
/project myproject    # Switch to 'myproject' (session preserved)
/project git@github.com:user/repo.git  # Clone and create new session
```

### Session & Bot Management
- `/session` - List available sessions
- `/set_session <id>` - Set current session
- `/current_session` - Show current session (auto-detects latest if not set)
- `/new_session` - Create new session  
- `/compact` - Compact current session (auto-detects latest if not set)
- `/compact <session_id>` - Compact specific session
- `/reset` - Clear current session
- `/restart` - Restart bot (clears all sessions, sends startup notification)

### General
- `/help` - Show help message
- Any message - Run OpenCode command with current project/session context

## Output Behavior

### Real-time Messages (Streamed)
- 📖 Reading: `src/file.py` (every occurrence, no deduplication)
- ✏️ Modifying: `README.md`
- 💻 Running: `git status`
- 🌐 Fetching: `https://example.com`
- 🔍 Searching: `**/*.py`
- 📋 Input: `command details` (if input > 500 chars, separate preview message)
- 📝 Session: `abc123...` (auto-extracted session ID)
- ⚠️ Error: `error message preview`

**Truncation Rules:**
- ≤100 chars: Show full input
- >100 chars: Truncate with "..."
- >500 chars: Separate message with 200 char preview

### Completion Messages
- 📊 Summary: Activity stats with file counts
- 📋 Full Details: AI response in chunks (3500 chars each)
- ✅ Completed: Final completion indicator

**Terminal**: Full DEBUG output with timestamps  
**Telegram**: All action messages streamed immediately + summary at end

## Requirements

- Python 3.9+
- `opencode` CLI installed and accessible
- Telegram bot token in `TELEGRAM_BOT_TOKEN` environment variable

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_telegram_chat_id_here"  # Optional
```

3. Run the bot:
```bash
python src/telegram_controller.py
```

## Project Management

Projects are stored in `~/projects/` directory:

- `/project` lists all git repositories in `~/projects/`
- Switching between projects preserves the current session
- Cloning a new project creates a new session
- Use `/reset` to manually create a new session

## Implementation Details

The bot uses JSON formatting for all OpenCode commands (`--format json`):

- **Action Messages**: Extracted from `tool_use` events with file/path details
- **Real-time Streaming**: Every tool execution is shown immediately (no deduplication)
- **Session Auto-Detection**: `/current_session` and `/compact` find latest session automatically
- **Session Extraction**: Automatic from `sessionID` events in opencode output
- **Error Handling**: Real-time error notifications from `error` events
- **Truncation**: Long values truncated to 100 chars + "...", inputs >500 chars sent separately
- **MarkdownV2 Formatting**: All messages properly escaped for Telegram MarkdownV2
- **Logging**: DEBUG level to terminal with timestamps

**Message Flow**:
```
[Command start]
  ↓
🔄 Typing indicator
  ↓
📖 Reading: src/file.py
📖 Reading: src/another.py    (every action shown)
✏️ Modifying: README.md       (no deduplication)
  ↓
⚠️ Error: optional error
  ↓
📊 Summary (activity stats)
📋 Full Details (if available)
  ↓
✅ Completed (typing stops)
```
[Command start]
  ↓
🔄 Typing indicator
  ↓
📖 Reading: src/file.py
✏️ Modifying: README.md  (real-time actions)
  ↓
⚠️ Error: optional error
  ↓
📊 Summary (activity stats)
📋 Full Details (if available)
  ↓
✅ Completed (typing stops)
```

## Folder Structure

```
opencode-telegram-bot/
├── src/
│   └── telegram_controller.py     # Main bot implementation
├── test/
│   └── test_telegram_controller.py # Unit tests
├── main.py                        # Entry point script
├── requirements.txt               # Python dependencies
├── README.md                      # This documentation
└── AGENTS.md                      # Implementation specification
```

## License

Apache License 2.0
