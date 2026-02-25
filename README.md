# OpenCode Telegram Controller

A Telegram bot that controls the OpenCode CLI tool.

## Features

- Manage OpenCode sessions via Telegram commands
- Execute `opencode run` commands
- Parse JSON/JSONL outputs
- Stream filtered results back to Telegram
- Automatically manage and track the current session

## Setup

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set your Telegram bot token as an environment variable:
```bash
export TELEGRAM_BOT_TOKEN="your_telegram_bot_token_here"
```

3. Run the bot:
```bash
python telegram_controller.py
```

## Commands

- `/session` - List all available sessions
- `/set_session <session_id>` - Set the current session
- `/current_session` - Show the current session
- Send any message to run it with opencode

## Architecture

The bot consists of several components:

1. **Telegram Bot Layer**
   - Handles commands and user messages
   - Sends responses back to Telegram

2. **Session Manager**
   - Stores and retrieves `current_session_id`
   - Interfaces with `opencode session list`

3. **OpenCode CLI Adapter**
   - Executes CLI commands:
     - `opencode session list --format json`
     - `opencode run --session ... --format json`
     - `opencode run --continue ... --format json`
   - Parses JSON and JSONL outputs

4. **Output Processor**
   - Filters out:
     - `type == "step_start"`
     - `type == "step_finish"`
   - Forwards remaining entries to Telegram