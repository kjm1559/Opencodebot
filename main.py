#!/usr/bin/env python3
"""
Main entry point for OpenCode Telegram Controller
"""

import sys
import os
import time
import requests
from src.telegram_controller import bot, logger, TELEGRAM_BOT_TOKEN, send_startup_message

POLLING_TIMEOUT = 30
POLLING_RETRY_DELAY = 5

def main():
    logger.info("Starting OpenCode Telegram Controller")
    if not TELEGRAM_BOT_TOKEN:
        logger.error("Telegram bot token not found")
        sys.exit(1)
    send_startup_message()
    
    retry_count = 0
    while True:
        try:
            bot.infinity_polling(timeout=POLLING_TIMEOUT, long_polling_timeout=POLLING_TIMEOUT + 5)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except requests.exceptions.ReadTimeout as e:
            retry_count += 1
            logger.warning(f"Read timeout (attempt {retry_count}): {e}")
            time.sleep(POLLING_RETRY_DELAY)
            if retry_count >= 10:
                logger.error("Too many timeout failures, exiting")
                sys.exit(1)
        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            logger.warning(f"Connection error (attempt {retry_count}): {e}")
            time.sleep(POLLING_RETRY_DELAY)
            if retry_count >= 10:
                logger.error("Too many connection failures, exiting")
                sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
