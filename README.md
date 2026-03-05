# OpenCode Telegram Controller

A Telegram bot that controls the OpenCode CLI via Telegram commands with intelligent typing indicators and session management.

## Features

- **Real-time Status Updates**: Tool execution status (file read/write, bash commands, etc.)
- **Summary Mode**: Clean emoji-based summary with detail view button
- **Logs to Terminal**: Full command output streamed to terminal, only summary to Telegram
- **Project Management**: List, switch, and clone projects with session awareness
- **Session Management**: Create, list, set, and reset sessions
- **Model Management**: List and set AI models from opencode
- **Status Monitoring**: View current model, project, and session status
- **Usage Statistics**: Track opencode usage with detailed statistics
- **Session History**: View and manage recent sessions
- **Command Cancellation**: Cancel running commands
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

### Session Management
- `/session` - List available sessions
- `/set_session <id>` - Set current session
- `/current_session` - Show current session
- `/new_session` - Create new session
- `/compact <session_id>` - Compact current session
- `/reset` - Clear current session

### General
- `/help` - Show help message
- Any message - Run OpenCode command with current project/session context

## Output Behavior

- **Terminal**: Full command output streamed in real-time
- **Telegram**: Only summary with:
  - Real-time tool status (📖 파일 읽는 중..., ✏️ 파일 수정 중..., 💻 명령어 실행 중...)
  - Final summary with emoji-based statistics
  - AI response preview (up to 2500 characters)

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
export TELEGRAM_CHAT_ID="your_telegram_chat_id_here"  # Optional, for restricting to specific chat
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

The bot uses JSON formatting for all OpenCode commands:

- **Filters**: `step_start`/`step_finish` messages excluded from Telegram
- **Real-time**: Tool execution status sent to Telegram (e.g., "📖 파일 읽는 중...")
- **Terminal**: Full output streamed to stdout for debugging
- **Telegram**: Only summary with emoji statistics and AI response preview

Summary includes:
- 📄 Files created
- ✏️ Files modified  
- 📖 Files read
- 💻 Bash commands executed
- ❌ Errors

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
