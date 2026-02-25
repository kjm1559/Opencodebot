# OpenCode Telegram Controller

A Telegram bot that controls the OpenCode CLI via Telegram commands with intelligent typing indicators and session management.

## Features

- **Session Management**: Create, list, set, and reset sessions
- **Command Execution**: Run OpenCode commands with real-time streaming output
- **Intelligent Typing Indicators**: Typing action stays active until command completion
- **Error Handling**: Comprehensive error reporting and logging
- **JSON Output Processing**: Properly handles and filters OpenCode JSONL output

## Commands

### Session Management
- `/session` - List available sessions
- `/set_session <id>` - Set current session
- `/current_session` - Show current session
- `/new_session` - Create new session
- `/compact <session_id>` - Compact current session
- `/reset` - Clear current session

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
├── test/
│   └── test_telegram_controller.py # Unit tests
├── main.py                        # Entry point script
├── requirements.txt               # Python dependencies
├── README.md                      # This documentation
└── AGENTS.md                      # Implementation specification
```

## License

MIT