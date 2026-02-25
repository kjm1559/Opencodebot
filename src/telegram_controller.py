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

def escape_md(text: str) -> str:
    """Escape markdown characters in text."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', text)

def process_output_line(line: str, chat_id: str) -> str:
    """Process a single line of opencode output and format it for Telegram."""
    try:
        # Check if line is JSON
        if not line:
            return ""
        obj = json.loads(line)
        
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
            escaped_input = escape_md(input_json)
            result += f"```\n"
            result += f"{escaped_input}\n"
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
    return session_store[chat_id].get("current_session_id")

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
                if formatted and formatted.strip():  # Check that formatted is not empty
                    # Send formatted message to Telegram
                    try:
                        logger.info(f"Sending to Telegram: {formatted[:100]}...")  # Log first 100 chars
                        bot.send_message(chat_id, formatted)
                    except Exception as e:
                        logger.error(f"Error sending message to Telegram: {e}")
                elif formatted:
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