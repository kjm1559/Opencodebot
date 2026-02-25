#!/bin/bash
# Run the OpenCode Telegram Controller

echo "Starting OpenCode Telegram Controller..."
echo "Bot token is set: $TELEGRAM_BOT_TOKEN"

# Make sure dependencies are installed
pip install -r requirements.txt

# Run the main script
python main.py