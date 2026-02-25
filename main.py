#!/usr/bin/env python3
"""
Main entry point for OpenCode Telegram Controller
"""

import sys
import os
from src.telegram_controller import bot, logger, TELEGRAM_BOT_TOKEN

def main():
    """Main entry point."""
    logger.info("Starting OpenCode Telegram Controller")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram bot token not found")
        sys.exit(1)
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()