#!/usr/bin/env python3
"""
Main entry point for OpenCode Telegram Controller
"""

import sys
import os
import time
import signal
import subprocess
import requests
from src.telegram_controller import bot, logger, TELEGRAM_BOT_TOKEN, send_startup_message, active_process

POLLING_TIMEOUT = 30
POLLING_RETRY_DELAY = 5

def cleanup_processes():
    """Clean up all active subprocesses before shutdown."""
    logger.info("Cleaning up active processes...")
    for chat_id, process in list(active_process.items()):
        if process.poll() is None:
            logger.info(f"Terminating process for chat {chat_id}")
            try:
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Killed unresponsive process for chat {chat_id}")
            except Exception as e:
                logger.error(f"Error terminating process for chat {chat_id}: {e}")
            finally:
                del active_process[chat_id]
    
    try:
        bot.stop_polling()
        logger.info("Stopped Telegram polling")
    except Exception as e:
        logger.error(f"Error stopping polling: {e}")

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    logger.info(f"Received signal {sig}, initiating shutdown...")
    cleanup_processes()
    sys.exit(0)

def main():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
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
            cleanup_processes()
            break
        except requests.exceptions.ReadTimeout as e:
            retry_count += 1
            logger.warning(f"Read timeout (attempt {retry_count}): {e}")
            if retry_count >= 10:
                logger.error("Too many timeout failures, initiating shutdown")
                cleanup_processes()
                sys.exit(1)
            time.sleep(POLLING_RETRY_DELAY)
        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            logger.warning(f"Connection error (attempt {retry_count}): {e}")
            if retry_count >= 10:
                logger.error("Too many connection failures, initiating shutdown")
                cleanup_processes()
                sys.exit(1)
            time.sleep(POLLING_RETRY_DELAY)
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            cleanup_processes()
            sys.exit(1)

if __name__ == "__main__":
    main()
