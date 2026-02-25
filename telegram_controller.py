#!/usr/bin/env python3
"""
Telegram Controller for OpenCode
This bot controls opencode via CLI commands through Telegram.
"""

import asyncio
import json
import logging
import subprocess
import sys
import os
from typing import Dict, List, Optional

# Telegram Bot imports
import telebot

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot configuration
# BOT_TOKEN should be set as an environment variable
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")

# Optional: Specific chat ID for restricted bot (or None for public bot)
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# In-memory session storage (use database in production)
# Structure: {chat_id: {"current_session_id": session_id}}
session_store: Dict[str, Dict[str, Optional[str]]] = {}

# Initialize the bot
bot = telebot.TeleBot(BOT_TOKEN)

def run_opencode_command(args: List[str]) -> subprocess.CompletedProcess:
    """Execute an opencode command and return the result."""
    try:
        result = subprocess.run(
            ["opencode"] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=300  # 5 minute timeout
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"opencode command failed: {e}")
        logger.error(f"stderr: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error("opencode command timed out")
        raise

def format_session_list(sessions_data: List[Dict]) -> str:
    """Format session list as a telegram message."""
    if not sessions_data:
        return "No sessions found."
    
    session_ids = [session.get('id', 'Unknown') for session in sessions_data]
    message = "Available Sessions:\n" + "\n".join([f"- {sid}" for sid in session_ids])
    return message

def get_current_session_id(chat_id: str) -> Optional[str]:
    """Get the current session ID for a chat."""
    if chat_id not in session_store:
        session_store[chat_id] = {"current_session_id": None}
    return session_store[chat_id]["current_session_id"]

def set_current_session_id(chat_id: str, session_id: str) -> None:
    """Set the current session ID for a chat."""
    if chat_id not in session_store:
        session_store[chat_id] = {"current_session_id": None}
    session_store[chat_id]["current_session_id"] = session_id

def is_valid_session_id(session_id: str, chat_id: str) -> bool:
    """Check if a session ID is valid by comparing against current session list."""
    try:
        result = run_opencode_command(["session", "list", "--format", "json"])
        sessions_data = json.loads(result.stdout)
        session_ids = [session.get('id', '') for session in sessions_data]
        return session_id in session_ids
    except Exception as e:
        logger.error(f"Error validating session ID: {e}")
        # If we can't validate, assume it's valid for now
        return True

def process_output_line(line: str, chat_id: str) -> Optional[str]:
    """
    Process a line of JSONL output from opencode run.
    Returns None if the line should be filtered out.
    """
    try:
        obj = json.loads(line)
        
        # Filter out step_start and step_finish messages
        if obj.get("type") in ["step_start", "step_finish"]:
            return None
            
        # Process other message types
        if obj.get("type") == "text":
            # Handle text messages that may be nested inside "part" object
            text_content = obj.get("text", "")
            if not text_content:
                # Try to extract from part.text if it's nested structure
                part = obj.get("part", {})
                text_content = part.get("text", "")
            return text_content
        elif obj.get("type") == "error":
            return f"Error: {obj.get('message', '')}"
        elif obj.get("type") == "command":
            return f"Command: {obj.get('command', '')}"
        elif obj.get("type") == "file":
            return f"File: {obj.get('path', '')} ({obj.get('size', '')})"
        elif obj.get("type") == "directory":
            return f"Directory: {obj.get('path', '')}"
        elif obj.get("type") == "completed":
            return "Operation completed successfully."
        elif obj.get("type") == "tool_use":
            # Extract tool name and inputs/outputs with proper status handling
            tool_name = "Unknown tool"
            inputs = {}
            outputs = {}
            status = ""
            
            # Try to extract from part object first (common in opencode)
            part = obj.get("part", {})
            if part:
                tool_name = part.get("tool", "Unknown tool")
                # Handle state dictionary for status and input
                state = part.get("state", {})
                status = state.get("status", "")
                inputs = state.get("input", {})
                outputs = state.get("output", {})
            else:
                # Fall back to direct fields if no part object
                tool_name = obj.get("tool_name", obj.get("tool", "Unknown tool"))
                inputs = obj.get("input", {})
                outputs = obj.get("output", {})
            
            # Format tool usage information with status in markdown code block - showing only input
            result = f"[{tool_name}]:\n"
            if status:
                result += f"Status: {status}\n"
            result += f"```\n"
            result += f"Input: {json.dumps(inputs, indent=2)}\n"
            result += f"```\n"
            return result.strip()
        else:
            # For unknown types, send raw message
            return json.dumps(obj, indent=2)
            
    except json.JSONDecodeError:
        # If line is not valid JSON, treat it as raw text
        return line.strip()

def format_message(obj: dict) -> str:
    """Format a message object for Telegram."""
    message_type = obj.get("type")
    
    if message_type == "text":
        return obj.get("text", "")
    elif message_type == "error":
        return f"Error: {obj.get('message', '')}"
    elif message_type == "command":
        return f"Running: {obj.get('command', '')}"
    elif message_type == "file":
        return f"Created file: {obj.get('path', '')}"
    elif message_type == "directory":
        return f"Created directory: {obj.get('path', '')}"
    elif message_type == "completed":
        return "Operation completed successfully."
    else:
        # JSON format for unknown types
        return json.dumps(obj, indent=2)

def stream_opencode_output(chat_id: str, command_args: List[str]) -> None:
    """Stream opencode command output to Telegram."""
    try:
        logger.info(f"Executing opencode command with args: {command_args}")
        process = subprocess.Popen(
            ["opencode"] + command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line buffered
        )
        
        # Read output line by line
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                logger.info(f"Raw opencode output line: {output.strip()}")
                formatted = process_output_line(output.strip(), chat_id)
                if formatted is not None and formatted.strip():  # Fixed: also check that formatted is not empty
                    # Send formatted message to Telegram
                    try:
                        logger.info(f"Sending to Telegram: {formatted[:100]}...")  # Log first 100 chars
                        bot.send_message(chat_id, formatted)
                    except Exception as e:
                        logger.error(f"Error sending message to Telegram: {e}")
                elif formatted is not None:
                    logger.warning("Skipping empty formatted message")
        
        # Check for errors
        stderr_output = process.stderr.read() if process.stderr else ""
        if stderr_output:
            logger.error(f"opencode stderr: {stderr_output}")
            bot.send_message(chat_id, f"Error: {stderr_output}")
        
        # Check the return code
        return_code = process.poll()
        if return_code != 0:
            logger.error(f"opencode command exited with code {return_code}")
            bot.send_message(chat_id, f"Command failed with exit code {return_code}")
        else:
            logger.info("Command completed successfully")
            
    except Exception as e:
        logger.error(f"Error streaming opencode output: {e}")
        bot.send_message(chat_id, f"Error occurred while running command: {str(e)}")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    """Send welcome message with instructions."""
    welcome_text = (
        "OpenCode Telegram Controller\n\n"
        "Commands:\n"
        "/session - List all available sessions\n"
        "/set_session <session_id> - Set the current session\n"
        "/current_session - Show the current session\n"
        "Send any message to run it with opencode\n\n"
        "Note: If no session is set, a new session will be created automatically."
    )
    bot.reply_to(message, welcome_text)

@bot.message_handler(commands=['session'])
def handle_session_list(message):
    """Handle /session command."""
    try:
        result = run_opencode_command(["session", "list", "--format", "json"])
        sessions_data = json.loads(result.stdout)
        formatted_sessions = format_session_list(sessions_data)
        bot.reply_to(message, formatted_sessions)
    except Exception as e:
        logger.error(f"Error in handle_session_list: {e}")
        bot.reply_to(message, f"Error retrieving sessions: {str(e)}")

@bot.message_handler(commands=['set_session'])
def handle_set_session(message):
    """Handle /set_session command."""
    # Extract session ID from message
    try:
        session_id = message.text.split(' ', 1)[1] if len(message.text.split(' ', 1)) > 1 else None
    except IndexError:
        session_id = None
        
    if not session_id:
        bot.reply_to(message, "Please provide a session ID. Usage: /set_session <session_id>")
        return
    
    # Validate session ID
    if not is_valid_session_id(session_id, str(message.chat.id)):
        bot.reply_to(message, "Invalid session ID.")
        return
    
    # Set session ID
    set_current_session_id(str(message.chat.id), session_id)
    bot.reply_to(message, f"Current session set to: {session_id}")

@bot.message_handler(commands=['current_session'])
def handle_current_session(message):
    """Handle /current_session command."""
    current_session_id = get_current_session_id(str(message.chat.id))
    if current_session_id:
        bot.reply_to(message, f"Current session: {current_session_id}")
    else:
        bot.reply_to(message, "No active session.")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular text messages."""
    chat_id = str(message.chat.id)
    user_message = message.text
    
    # If chat ID is specified, only respond to that chat
    if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
        return
    
    # Get current session ID
    current_session_id = get_current_session_id(chat_id)
    
    # For debugging purposes to see what's happening
    logger.info(f"Received message from chat {chat_id}, current session: {current_session_id}")
    
    # Send a message indicating command execution has started
    # Use Telegram's typing indicator instead of text message
    try:
        bot.send_chat_action(chat_id, 'typing')
    except Exception as e:
        logger.error(f"Failed to send typing indicator: {e}")
        # Fallback to text message if typing indicator fails
        bot.reply_to(message, "Executing command... Please wait.")
    
    if current_session_id:
        # Using existing session
        logger.info(f"Running opencode with existing session {current_session_id}")
        command_args = ["run", "--session", current_session_id, user_message, "--format", "json"]
    else:
        # Create new session
        logger.info("Creating new session")
        command_args = ["run", "--continue", user_message, "--format", "json"]
    
    # Stream output to Telegram
    try:
        stream_opencode_output(chat_id, command_args)
    except Exception as e:
        logger.error(f"Error in handle_message: {e}")
        bot.reply_to(message, f"Error occurred: {str(e)}")

def main():
    """Main entry point."""
    logger.info("Starting OpenCode Telegram Controller")
    if not BOT_TOKEN:
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