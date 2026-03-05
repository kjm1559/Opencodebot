# OpenCode Telegram Controller

A Telegram bot that controls the OpenCode CLI via Telegram commands with intelligent typing indicators and session management.

## Features

- **Status Monitoring**: View current model, project, and session status
- **Usage Statistics**: Track opencode usage with detailed statistics
- **Session History**: View and manage recent sessions
- **Command Cancellation**: Cancel running commands
- **Model Management**: List and set AI models from opencode
- **Project Management**: Set and manage project workspace directories
- **Session Management**: Create, list, set, and reset sessions
- **Command Execution**: Run OpenCode commands with real-time streaming output
- **Intelligent Typing Indicators**: Typing action stays active until command completion
- **Error Handling**: Comprehensive error reporting and logging
- **JSON Output Processing**: Properly handles and filters OpenCode JSONL output
- **Workspace Support**: Dedicated workspace directory for project management (git clone, folders)

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
- `/project [path]` - Set or show current project path
- `/project /path/to/workspace` - Set workspace directory for project operations

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

### Typing Control
- Typing indicators sent only at command start
- Remains active until command completion
- "Command completed successfully" signals typing indicator removal

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
python main.py
```

## Implementation Details

The bot uses JSON formatting for all OpenCode commands and filters out `step_start`/`step_finish` messages. It streams output to Telegram in real-time and properly handles large outputs with error management.

## Folder Structure

```
opencode-telegram-bot/
├── src/
│   └── telegram_controller.py     # Main bot implementation
├── workspace/                     # Project workspace directory
│   ├── project1/                  # Managed projects
│   └── project2/
├── test/
│   └── test_telegram_controller.py # Unit tests
├── main.py                        # Entry point script
├── requirements.txt               # Python dependencies
├── README.md                      # This documentation
└── AGENTS.md                      # Implementation specification
```

## Workspace Management

The bot supports a `/workspace` directory for project management:

- Use `/project /home/mj/project/Opencodebot/workspace/myproject` to set a project path
- Multiple projects can be managed in separate subdirectories
- Sessions are automatically associated with projects

## License

MIT