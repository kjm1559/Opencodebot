# OpenCode Telegram Controller

A Telegram bot that controls OpenCode via CLI commands.

## Features

- Execute opencode commands via Telegram
- Manage sessions per chat
- Parse and format JSON/JSONL outputs from opencode
- Display tool_use messages with only input information in markdown code blocks
- Handle text messages with proper nested structure extraction
- Provide user feedback during command execution
- Include proper logging and error handling
- Automatic session creation when no session is set
- Filter out step_start and step_finish messages
- Dot-only escaping for Telegram MarkdownV2 compatibility

## Setup

1. Install the required packages:
```bash
pip install -r requirements.txt
```

2. Set environment variables:
```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
export TELEGRAM_CHAT_ID="your_telegram_chat_id_here"  # Optional, for restricting to specific chat
```

3. Run the bot:
```bash
python main.py
```

## Commands

- `/session` - List all available sessions
- `/set_session <session_id>` - Set the current session
- `/current_session` - Show the current session
- Send any message to run it with opencode

## Usage

1. Start the bot and send any message to begin using opencode
2. If no session is set, a new session will be created automatically
3. All output from opencode will be processed and sent to Telegram
4. Tool_use messages are formatted with only input information in markdown code blocks
5. Text messages are properly extracted from their nested structure
6. step_start and step_finish messages are automatically filtered out

## Requirements

- Python 3.6+
- opencode CLI installed and in PATH
- telebot library

## Folder Structure

```
opencode-telegram-bot/
├── src/
│   └── telegram_controller.py     # Main bot implementation
├── test/
│   └── test_telegram_controller.py # Unit tests
├── main.py                        # Entry point script
├── run_bot.sh                     # Execution script
├── requirements.txt               # Python dependencies
├── README.md                      # This documentation
└── AGENTS.md                      # Implementation specification
```

## Example Output

For tool_use messages:
```
[tool_name]:
Status: success
```
```json
{
  "param1": "value1",
  "param2": "value2"
}
```

For text messages:
```
Hello world!
```

## Error Handling

- Invalid session IDs are rejected
- Command execution errors are logged and sent to Telegram
- Empty messages are skipped
- JSON parsing errors are handled gracefully
- Automatic fallback to new session creation when needed

## Development

### Implementation Status
- All syntax errors have been fixed
- Complete functionality implemented
- Infinite loop concerns resolved
- All unit tests pass (10/10)

### Key Improvements
- Robust session management with automatic fallback
- Proper filtering of step_start/step_finish messages
- Dot-only escaping for Telegram MarkdownV2 compatibility
- Comprehensive error handling and logging
- Performance optimizations