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
MAX_RETRY_DELAY = 300  # 5 minutes max delay

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
        if bot:
            bot.stop_polling()
            logger.info("Stopped Telegram polling")
    except Exception as e:
        logger.warning(f"Warning stopping polling: {e}")

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
    retry_delay = POLLING_RETRY_DELAY
    
    while True:
        try:
            bot.infinity_polling(timeout=POLLING_TIMEOUT, long_polling_timeout=POLLING_TIMEOUT + 5)
            
            # Connection successful - reset retry counters
            retry_count = 0
            retry_delay = POLLING_RETRY_DELAY
            
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            cleanup_processes()
            break
        except requests.exceptions.ConnectionError as e:
            retry_count += 1
            logger.warning(f"Connection error (attempt {retry_count}, delay {retry_delay}s): {e}")
            
            # Exponential backoff with cap
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            
            logger.info(f"Waiting {retry_delay}s before reconnecting...")
            time.sleep(retry_delay)
            
        except requests.exceptions.ReadTimeout as e:
            retry_count += 1
            logger.warning(f"Read timeout (attempt {retry_count}): {e}")
            
            # Exponential backoff with cap
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            
            logger.info(f"Waiting {retry_delay}s before retry...")
            time.sleep(retry_delay)
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            cleanup_processes()
            sys.exit(1)

if __name__ == "__main__":
    main()
