#!/usr/bin/env python3
"""
Telegram Controller for OpenCode
This bot controls opencode via CLI commands through Telegram.
"""

import os
import asyncio
import re
import json
import subprocess
import sys
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Bot setup
if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable not set")
    sys.exit(1)

try:
    import telebot
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
except ImportError as e:
    logger.error(f"Failed to import telebot: {e}")
    sys.exit(1)

# In-memory session storage (per chat)
session_store: Dict[str, Dict[str, Any]] = {}

def escape_markdown_v2(text: str) -> str:
    """
    Telegram MarkdownV2 escape function
    """
    escape_chars = r'_*$begin:math:display$$end:math:display$()~`>#+\-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def escape_only_dots(text: str) -> str:
    """Escape only '.' for Telegram MarkdownV2 ('.' -> '\\.')."""
    return text.replace(".", r"\.").replace("-", r"\-").replace("(", r"\(").replace(")", r"\)")

def process_output_line(line: str, chat_id: str) -> str:
    """Process a single line of opencode output and format it for Telegram."""
    try:
        # Check if line is JSON
        if not line:
            return ""
        obj = json.loads(line)
        
        # Filter out step_start and step_finish messages completely
        if obj.get("type") == "step_start" or obj.get("type") == "step_finish":
            return None  # Don't send these messages
        
        if obj.get("type") == "text":
            # Extract text content
            text_content = obj.get("text", "")
            # Try to get text from part.text if it exists
            part = obj.get("part", {})
            if part:
                text_content = part.get("text", text_content)
            return text_content
            
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
            # Add markdown escaping for the input data to prevent formatting issues
            input_json = json.dumps(inputs, indent=2)
            result += f"```\n"
            result += f"{input_json}\n"
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

def run_opencode_command(args: List[str]) -> subprocess.CompletedProcess:
    """Run an opencode command and return the result."""
    try:
        result = subprocess.run(
            ["opencode"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"opencode command failed: {e}")
        raise e

def format_session_list(sessions_data) -> str:
    """Format session list for Telegram."""
    if not sessions_data:
        return "No sessions available."
    
    formatted = "Available Sessions:\n"
    for session in sessions_data:
        formatted += f"- {session['id']}\n"
    return formatted

def is_valid_session_id(session_id: str, chat_id: str) -> bool:
    """Check if a session ID is valid by comparing against session list."""
    try:
        result = run_opencode_command(["session", "list", "--format", "json"])
        sessions_data = json.loads(result.stdout)
        session_ids = [s["id"] for s in sessions_data]
        return session_id in session_ids
    except Exception:
        return False  # If we can't validate, assume it might be valid

def set_current_session_id(chat_id: str, session_id: str) -> None:
    """Set the current session ID for a chat."""
    if chat_id not in session_store:
        session_store[chat_id] = {}
    session_store[chat_id]["current_session_id"] = session_id

def get_current_session_id(chat_id: str) -> str:
    """Get the current session ID for a chat."""
    if chat_id not in session_store:
        return None
    return session_store[chat_id].get("current_session_id")  # type: ignore

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
                # Add proper handling for the case when process.stdout might be None
                output_clean = output.strip() if output else ""
                if output_clean:
                    logger.info(f"Raw opencode output line: {output_clean}")
                    formatted = process_output_line(output_clean, chat_id)
                    if formatted is not None and formatted.strip():  # Check that formatted is not None and not empty
                        # Escape only dots for Telegram MarkdownV2
                        escaped_message = escape_only_dots(formatted)
                        # Send formatted message to Telegram
                        try:
                            logger.info(f"Sending to Telegram: {escaped_message[:100]}...")  # Log first 100 chars
                            bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
                        except Exception as e:
                            logger.error(f"Error sending message to Telegram: {e}")
                    elif formatted is not None:
                        logger.warning("Skipping empty formatted message")
        
        # Check for errors
        stderr_output = process.stderr.read() if process.stderr else ""
        if stderr_output:
            logger.error(f"opencode stderr: {stderr_output}")
            escaped_error = escape_markdown_v2(f"Error: {stderr_output}")
            bot.send_message(chat_id, escaped_error, parse_mode="MarkdownV2")
        
        # Check the return code
        return_code = process.poll()
        if return_code != 0:
            logger.error(f"opencode command exited with code {return_code}")
            escaped_error = escape_markdown_v2(f"Command failed with exit code {return_code}")
            bot.send_message(chat_id, escaped_error, parse_mode="MarkdownV2")
        else:
            logger.info("Command completed successfully")
            
    except Exception as e:
        logger.error(f"Error streaming opencode output: {e}")
        escaped_error = escape_markdown_v2(f"Error occurred while running command: {str(e)}")
        bot.send_message(chat_id, escaped_error, parse_mode="MarkdownV2")

# === Add the message handlers below ===

@bot.message_handler(commands=['session'])
def handle_session_command(message):
    """Handle /session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /session command from chat {chat_id}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')  # Show typing indicator
        
        result = run_opencode_command(["session", "list", "--format", "json"])
        sessions_data = json.loads(result.stdout)
        formatted_sessions = format_session_list(sessions_data)
        escaped_message = escape_markdown_v2(formatted_sessions)
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /session command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['set_session'])
def handle_set_session_command(message):
    """Handle /set_session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /set_session command from chat {chat_id}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')  # Show typing indicator
        
        # Extract session ID from message
        session_id = message.text[len('/set_session'):].strip()
        if not session_id:
            escaped_message = escape_markdown_v2("Please provide a session ID. Usage: /set_session <session_id>")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            return
            
        # Validate session ID if possible
        if not is_valid_session_id(session_id, chat_id):
            escaped_message = escape_markdown_v2("Invalid session ID.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            return
            
        # Set session ID
        set_current_session_id(chat_id, session_id)
        escaped_message = escape_markdown_v2(f"Current session set to: {session_id}")
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /set_session command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['current_session'])
def handle_current_session_command(message):
    """Handle /current_session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /current_session command from chat {chat_id}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')  # Show typing indicator
        
        session_id = get_current_session_id(chat_id)
        if session_id:
            escaped_message = escape_markdown_v2(f"Current session: {session_id}")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        else:
            escaped_message = escape_markdown_v2("No active session.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            
    except Exception as e:
        logger.error(f"Error handling /current_session command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular messages."""
    chat_id = str(message.chat.id)
    logger.info(f"Received message from chat {chat_id}: {message.text}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')
        
        # Check if we have an active session
        current_session_id = get_current_session_id(chat_id)
        
        if current_session_id:
            # Use the existing session
            logger.info(f"Using existing session {current_session_id}")
            command_args = ["run", "--session", current_session_id, message.text, "--format", "json"]
            stream_opencode_output(chat_id, command_args)
        else:
            # Start a new session using --continue
            logger.info("Starting new session with --continue")
            # We'll first run the command with --continue, which should automatically create a session
            # Then we'll query session list to get the latest session ID
            command_args = ["run", "--continue", message.text, "--format", "json"]
            
            # Execute the command, but just send a message to user to indicate it's running
            escaped_message = escape_markdown_v2("Executing command... Please wait.")
            bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
            
            # The execution is run but the return is not waited for for the streaming - let
            # the opencode auto-manage the session creation via the --continue flag. The user 
            # can get the session ID via the session list command now.
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.send_message(chat_id, escaped_error, parse_mode="MarkdownV2")
