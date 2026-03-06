#!/usr/bin/env python3
"""
Telegram Controller for OpenCode
This bot controls opencode via CLI commands through Telegram.
"""

import os
import re
import json
import subprocess
import sys
from typing import List, Dict, Any, Optional
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

# Set bot commands for Telegram UI
try:
    from telebot import types
    bot.set_my_commands([
        types.BotCommand("status", "Show current status (model, project, session)"),
        types.BotCommand("stats", "Show opencode usage statistics"),
        types.BotCommand("history", "Show recent session history"),
        types.BotCommand("cancel", "Cancel current command"),
        types.BotCommand("project", "Set/List current project path"),
        types.BotCommand("model", "List/Set current model"),
        types.BotCommand("session", "List available sessions"),
        types.BotCommand("set_session", "Set current session"),
        types.BotCommand("current_session", "Show current session"),
        types.BotCommand("new_session", "Create new session"),
        types.BotCommand("compact", "Compact current session"),
        types.BotCommand("reset", "Clear current session"),
        types.BotCommand("help", "Show this help message"),
    ])
    logger.info("Successfully set bot commands")
except Exception as e:
    logger.error(f"Failed to set bot commands: {e}")

# In-memory storage (per chat)
session_store: Dict[str, Dict[str, Any]] = {}
project_store: Dict[str, str] = {}
model_store: Dict[str, str] = {}
active_process: Dict[str, Any] = {}  # Track active processes for cancel

# Configuration constants
COMMAND_TIMEOUT = 300  # 5 minutes timeout for commands
MAX_MESSAGE_LENGTH = 4096  # Telegram message limit
MAX_PREVIEW_LENGTH = 2500  # Max characters for response preview

def escape_markdown_v2(text: str) -> str:
    """
    Telegram MarkdownV2 escape function
    """
    # Characters that need to be escaped in MarkdownV2
    escape_chars = r'_*$()~`>#+\-=|{}.!'
    # Use re.escape on each character and create a pattern to match any of these characters
    escaped_text = re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)
    return escaped_text

def escape_only_dots(text: str) -> str:
    """Escape only '.' for Telegram MarkdownV2 ('.' -> '\\.')."""
    return text.replace(".", r"\.").replace("-", r"\-").replace("(", r"\(").replace(")", r"\)").replace("_", r"\_").replace("#", r"\#").replace("!", r"\!").replace("=", r"\=").replace("+", r"\+")

def collect_output_for_summary():
    """Initialize output collection."""
    return {"lines": [], "summary": None, "full_text": ""}

def process_line_for_summary(collect_data: dict, line: str) -> None:
    """Process a line and add to collection."""
    if collect_data["lines"] is None:
        collect_data["lines"] = []
    
    try:
        if not line:
            return
        obj = json.loads(line)
        collect_data["lines"].append(obj)
    except json.JSONDecodeError:
        pass

def summarize_output(lines: List[dict]) -> dict:
    """Summarize output into key metrics."""
    summary = {
        "files_created": 0,
        "files_modified": 0,
        "files_read": 0,
        "bash_commands": 0,
        "errors": 0,
        "final_text": ""
    }
    
    for obj in lines:
        msg_type = obj.get("type")
        
        if msg_type == "file":
            summary["files_created"] += 1
        elif msg_type == "directory":
            pass  # Ignore directories in summary
        elif msg_type == "tool_use":
            tool_info = obj.get("part", {}).get("tool", "")
            if "read" in tool_info:
                summary["files_read"] += 1
            elif "write" in tool_info:
                summary["files_created"] += 1
            elif "edit" in tool_info:
                summary["files_modified"] += 1
            elif "bash" in tool_info:
                summary["bash_commands"] += 1
            elif "glob" in tool_info:
                pass  # File search
            elif "grep" in tool_info:
                pass  # Text search
        elif msg_type == "text":
            text = obj.get("text", "") or obj.get("part", {}).get("text", "")
            if text.strip():
                summary["final_text"] += text + "\n"
        elif msg_type == "error":
            summary["errors"] += 1
    
    return summary

def format_summary_message(summary: dict, detail_text: str = "") -> tuple:
    """Format summary into a readable message with inline keyboard."""
    from telebot import types
    
    # Create message text
    message_lines = []
    
    # Add response text if available (this is the main content!)
    if summary["final_text"]:
        text = summary["final_text"].strip()
        if len(text) > 2500:
            text = text[:2500] + "..."
        
        # Escape special chars for summary
        escaped_text = text.replace("\n", "\n")
        
        message_lines.append("💬 Response:\n")
        message_lines.append(f"{escaped_text}\n")
    
    # Build emoji-based summary
    emoji_parts = []
    
    if summary["files_created"] > 0:
        emoji_parts.append(f"📄 {summary['files_created']} files created")
    if summary["files_modified"] > 0:
        emoji_parts.append(f"✏️ {summary['files_modified']} files modified")
    if summary["files_read"] > 0:
        emoji_parts.append(f"📖 {summary['files_read']} files read")
    if summary["bash_commands"] > 0:
        emoji_parts.append(f"💻 {summary['bash_commands']} commands executed")
    
    if summary["errors"] > 0:
        emoji_parts.append(f"❌ {summary['errors']} errors")
    
    if emoji_parts:
        message_lines.append("\n✨ Activities:\n")
        for item in emoji_parts:
            message_lines.append(f"  • {item}\n")
    
    # Create inline keyboard for detail view
    buttons = []
    if detail_text and len(detail_text.strip()) > 0 and len(detail_text) > 2500:
        button = types.InlineKeyboardButton("📋 View Full Output", callback_data=f"details_{hash(detail_text[:50])}")
        buttons.append([button])
    
    keyboard = types.InlineKeyboardMarkup().add(*buttons) if buttons else None
    
    return "".join(message_lines), keyboard, detail_text

def process_output_line(line: str, chat_id: str) -> str:
    """Process a single line of opencode output and format it for Telegram."""
    try:
        # Check if line is JSON
        if not line:
            return ""
        obj = json.loads(line)
        
        # Filter out step_start and step_finish messages completely
        if obj.get("type") == "step_start" or obj.get("type") == "step_finish":
            return ""  # Don't send these messages
        
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
            
    except json.JSONDecodeError as e:
        # If line is not valid JSON, treat it as raw text
        # Also handle the specific "Extra data" error which can happen when JSON parsing is attempted on partial data
        if "Extra data" in str(e):
            logger.warning(f"Skipping line due to extra data in JSON: {line[:50]}.")
            return ""
        # If it's not an "Extra data" error, we still want to be careful about parsing
        # This error likely occurs when there's malformed JSON, or multiple JSON objects on one line
        logger.debug(f"JSON parse error: {e}; raw line: {line}")
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

def run_opencode_command(args: List[str], timeout: int = COMMAND_TIMEOUT) -> subprocess.CompletedProcess:
    """Run an opencode command and return the result."""
    try:
        result = subprocess.run(
            ["opencode"] + args,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"opencode command timed out after {timeout} seconds")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"opencode command failed: {e}")
        raise

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
        return ""
    session_id = session_store[chat_id].get("current_session_id")
    return session_id if session_id is not None else ""

def set_current_project(chat_id: str, project_path: str) -> None:
    """Set the current project path for a chat."""
    project_store[chat_id] = project_path

def get_current_project(chat_id: str) -> str:
    """Get the current project path for a chat."""
    return project_store.get(chat_id, "")

def list_projects() -> List[str]:
    """List all projects in ~/projects/ directory."""
    projects_dir = os.path.expanduser("~/projects")
    if not os.path.exists(projects_dir):
        return []
    
    projects = []
    for item in os.listdir(projects_dir):
        item_path = os.path.join(projects_dir, item)
        if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, ".git")):
            projects.append(item)
    return sorted(projects)

def get_project_path(project_name: str) -> str:
    """Get full path for a project by name."""
    return os.path.join(os.path.expanduser("~/projects"), project_name)

def set_current_model(chat_id: str, model_name: str) -> None:
    """Set the current model for a chat."""
    model_store[chat_id] = model_name

def get_current_model(chat_id: str) -> str:
    """Get the current model for a chat."""
    return model_store.get(chat_id, "")

def get_available_models() -> List[str]:
    """Get list of available models from opencode."""
    try:
        result = run_opencode_command(["models"], timeout=10)
        models = result.stdout.strip().split("\n")
        return [m.strip() for m in models if m.strip()]
    except Exception:
        return []

def get_tool_status_message(tool_name: str, status: str) -> Optional[str]:
    """Get a short status message for tool execution."""
    TOOL_STATUS_MAP = {
        "read_file": ("reading", "📖 Reading file..."),
        "edit_file": ("editing", "✏️ Modifying file..."),
        "write_file": ("writing", "📄 Writing file..."),
        "bash": ("running", "💻 Running command..."),
        "webfetch": ("fetching", "🌐 Fetching web..."),
        "glob": ("searching", "🔍 Searching files..."),
        "grep": ("searching", "🔍 Searching text...")
    }
    
    tool_info = TOOL_STATUS_MAP.get(tool_name)
    if tool_info and tool_info[0] in status:
        return tool_info[1]
    return None

def stream_opencode_output(chat_id: str, command_args: List[str]) -> None:
    """Stream opencode command output to terminal, send only summary to Telegram."""
    try:
        bot.send_message(chat_id, escape_markdown_v2("🔄 Started..."), parse_mode="MarkdownV2")
        
        logger.info(f"Executing opencode command with args: {command_args}")
        
        process = subprocess.Popen(
            ["opencode"] + command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        collect_data = collect_output_for_summary()
        last_tool_status: Optional[str] = None
        
        # Stream stdout
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                    
                print(line, flush=True)
                process_line_for_summary(collect_data, line)
                
                # Send tool status to Telegram
                try:
                    obj = json.loads(line)
                    if obj.get("type") == "tool_use":
                        part = obj.get("part", {})
                        tool_name = part.get("tool", "")
                        status = part.get("state", {}).get("status", "")
                        
                        status_msg = get_tool_status_message(tool_name, status)
                        if status_msg and status_msg != last_tool_status and "finished" not in status:
                            last_tool_status = status_msg
                            try:
                                bot.send_message(chat_id, escape_markdown_v2(status_msg), parse_mode="MarkdownV2")
                            except Exception as e:
                                logger.warning(f"Failed to send status: {e}")
                except json.JSONDecodeError:
                    pass
        
        # Stream stderr
        if process.stderr:
            for line in process.stderr:
                print(f"STDERR: {line.strip()}", flush=True)
        
        return_code = process.poll()
        if return_code != 0:
            logger.error(f"opencode command exited with code {return_code}")
        
        # Generate and send summary
        summary = summarize_output(collect_data.get("lines", []))
        full_text = summary.get("final_text", "")
        
        logger.info(f"Summary: {summary}")
        
        summary_text, keyboard, _ = format_summary_message(summary, full_text)
        if not summary_text.strip():
            summary_text = "✅ Completed"
        
        escaped_summary = escape_only_dots(summary_text)
        logger.info(f"Sending summary: {len(escaped_summary)} chars")
        
        try:
            bot.send_message(
                chat_id,
                f"📊 요약:\n{escaped_summary}",
                parse_mode="MarkdownV2",
                reply_markup=keyboard
            )
            logger.info("Summary sent successfully")
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            try:
                bot.send_message(chat_id, f"📊 요약:\n{summary_text}")
            except Exception as e2:
                logger.error(f"Error sending plain summary: {e2}")
        
        bot.send_message(
            chat_id,
            escape_markdown_v2("━─━─━─━─━─━─━─━─\n✅ Completed"),
            parse_mode="MarkdownV2"
        )
        
        if return_code == 0:
            logger.info("Command completed successfully")
        
    except Exception as e:
        logger.error(f"Error streaming opencode output: {e}")
        bot.send_message(
            chat_id,
            escape_markdown_v2(f"❌ Error: {str(e)}"),
            parse_mode="MarkdownV2"
        )

@bot.message_handler(commands=['project'])
def handle_project_command(message):
    """Handle /project command - list projects, switch to project, or clone new project."""
    chat_id = str(message.chat.id)
    project_input = message.text[len('/project'):].strip()
    
    if not project_input:
        # List all projects
        projects = list_projects()
        current_project = get_current_project(chat_id)
        
        if not projects:
            bot.reply_to(
                message,
                escape_markdown_v2("📁 No projects in ~/projects/\n\nYou can clone with: /project \u003cgit-url>"),
                parse_mode="MarkdownV2"
            )
            return
        
        response = "📁 Available Projects:\n\n"
        for i, proj in enumerate(projects, 1):
            marker = "✅" if current_project and proj in current_project else " "
            response += f"{marker} {i}. {proj}\n"
        
        if current_project:
            response += f"\n📍 Current: {current_project}"
        else:
            response += "\n📍 No project selected" + "\n\nUse /project \u003cnumber> or /project \u003cgit-url>"
        
        bot.reply_to(message, escape_markdown_v2(response), parse_mode="MarkdownV2")
        return
    
    # Handle project number
    if project_input.isdigit():
        projects = list_projects()
        idx = int(project_input) - 1
        
        if 0 <= idx < len(projects):
            set_current_project(chat_id, get_project_path(projects[idx]))
            bot.reply_to(
                message,
                escape_markdown_v2(f"📁 Switched to: {projects[idx]}\n🔄 Session preserved"),
                parse_mode="MarkdownV2"
            )
        else:
            bot.reply_to(message, escape_markdown_v2("❌ Invalid project number"), parse_mode="MarkdownV2")
        return
    
    # Handle git URL
    if project_input.startswith(('git@', 'http://', 'https://', 'git://')):
        bot.send_message(chat_id, escape_markdown_v2("🔄 Cloning..."), parse_mode="MarkdownV2")
        
        try:
            repo_name = project_input.split('/')[-1].replace('.git', '')
            clone_path = os.path.expanduser(f"~/projects/{repo_name}")
            os.makedirs(os.path.dirname(clone_path), exist_ok=True)
            
            result = subprocess.run(
                ['git', 'clone', project_input, clone_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                bot.reply_to(message, escape_markdown_v2(f"❌ Clone failed: {result.stderr}"), parse_mode="MarkdownV2")
                return
            
            set_current_project(chat_id, clone_path)
            set_current_session_id(chat_id, "")
            bot.reply_to(
                message,
                escape_markdown_v2(f"📁 Cloned: {repo_name}\n✨ New session created"),
                parse_mode="MarkdownV2"
            )
        except subprocess.TimeoutExpired:
            bot.reply_to(message, escape_markdown_v2("❌ Clone timed out"), parse_mode="MarkdownV2")
        except Exception as e:
            bot.reply_to(message, escape_markdown_v2(f"❌ Error: {str(e)}"), parse_mode="MarkdownV2")
        return
    
    # Handle project name or path
    projects = list_projects()
    if project_input in projects:
        set_current_project(chat_id, get_project_path(project_input))
        bot.reply_to(
            message,
            escape_markdown_v2(f"📁 Switched to: {project_input}\n🔄 Session preserved"),
            parse_mode="MarkdownV2"
        )
    elif os.path.exists(project_input):
        set_current_project(chat_id, project_input)
        bot.reply_to(message, escape_markdown_v2(f"📁 Set: {project_input}"), parse_mode="MarkdownV2")
    else:
        bot.reply_to(message, escape_markdown_v2(f"❌ Not found: {project_input}"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['help'])
def handle_help_command(message):
    """Handle /help command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /help command from chat {chat_id}")
    
    try:
        help_text = (
            "OpenCode Telegram Controller Help:\n\n"
            "Commands:\n"
            "/status - Show current status\n"
            "/stats - Show usage statistics\n"
            "/history - Show recent sessions\n"
            "/cancel - Cancel running command\n"
            "/project - List available projects\n"
            "/project <number> - Switch to project by number (keeps session)\n"
            "/project <git-url> - Clone new project (creates new session)\n"
            "/model [name] - List/set current model\n"
            "/session - List available sessions\n"
            "/set_session \u003cid\u003e - Set current session\n"
            "/current_session - Show current session\n"
            "/new_session - Create new session\n"
            "/compact \u003csession_id\u003e - Compact current session\n"
            "/reset - Clear current session\n"
            "/help - Show this help message\n\n"
            "Simply type any message to run opencode commands."
        )
        escaped_message = escape_markdown_v2(help_text)
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /help command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['session'])
def handle_session_command(message):
    """Handle /session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /session command from chat {chat_id}")
    
    try:
        # Show typing indicator for long-running operations
        bot.send_chat_action(chat_id, 'typing')
        
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

@bot.message_handler(commands=['new_session'])
def handle_new_session_command(message):
    """Handle /new_session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /new_session command from chat {chat_id}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')
        
        # Create a new session by running a simple command - let opencode handle session creation automatically
        escaped_message = escape_markdown_v2("Creating new session... Please wait.")
        bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
        
        # Run a simple command that will trigger session creation
        # We don't need to use --continue here since opencode creates session automatically
        # Use a simple command instead of "new session"
        command_args = ["run", "create a new session", "--format", "json"]
        result = run_opencode_command(command_args)
        
        # Get the latest session to make sure we have access to it
        try:
            result = run_opencode_command(["session", "list", "--format", "json"])
            sessions_data = json.loads(result.stdout)
            if sessions_data:
                # Take the first available session (usually the most recent one)
                # Instead of trying to sort by timestamps, we'll take the first one for simplicity
                selected_session_id = sessions_data[0]['id']
                set_current_session_id(chat_id, selected_session_id)
                escaped_message = escape_markdown_v2(f"New session created and set: {selected_session_id}")
                bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            else:
                escaped_message = escape_markdown_v2("New session created but unable to determine session ID.")
                bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        except Exception as e:
            logger.error(f"Error getting session list after creating new session: {e}")
            # If we can't get the latest session, let's try to create a better fallback
            escaped_message = escape_markdown_v2("New session created successfully (ID not determinable).")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
                
    except Exception as e:
        logger.error(f"Error handling /new_session command: {e}")
        escaped_error = escape_markdown_v2(f"Error creating new session: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['compact'])
def handle_compact_command(message):
    """Handle /compact command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /compact command from chat {chat_id}")
    
    try:
        # Check if we have an active session
        session_id = get_current_session_id(chat_id)
        if not session_id:
            escaped_message = escape_markdown_v2("No active session.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            return
            
        # Compact the current session
        command_args = ["session", "compact", session_id]
        result = run_opencode_command(command_args)
        
        escaped_message = escape_markdown_v2(f"Session compacted successfully: {session_id}")
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /compact command: {e}")
        escaped_error = escape_markdown_v2(f"Error compacting session: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['reset'])
def handle_reset_command(message):
    """Handle /reset command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /reset command from chat {chat_id}")
    
    try:
        # Clear the current session ID to force creation of a new session
        set_current_session_id(chat_id, "")
        escaped_message = escape_markdown_v2("Session has been reset. A new session will be created for the next command.")
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /reset command: {e}")
        escaped_error = escape_markdown_v2(f"Error resetting session: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['model'])
def handle_model_command(message):
    """Handle /model command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /model command from chat {chat_id}")
    
    try:
        bot.send_chat_action(chat_id, 'typing')
        
        model_arg = message.text[len('/model'):].strip()
        
        if not model_arg:
            # Show current model and available models
            current_model = get_current_model(chat_id)
            
            # Get available models
            available_models = get_available_models()
            
            response = "Available Models:\n"
            if available_models:
                for model in available_models[:20]:  # Limit to first 20 for readability
                    response += f"- {model}\n"
                if len(available_models) > 20:
                    response += f"... and {len(available_models) - 20} more\n"
            else:
                response += "Unable to fetch models.\n"
            
            if current_model:
                response += f"\n🔵 Current model: {current_model}"
            else:
                response += "\nNo model set (using opencode default)"
            
            escaped_message = escape_markdown_v2(response)
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        else:
            # Set model
            model_name = model_arg
            
            # Validate model by checking if it's in available models
            available_models = get_available_models()
            if model_name in available_models:
                set_current_model(chat_id, model_name)
                escaped_message = escape_markdown_v2(f"Model set to: {model_name}")
                bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            else:
                escaped_message = escape_markdown_v2(f"Model '{model_name}' not found. Use /model to list available models.")
                bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
                
    except Exception as e:
        logger.error(f"Error handling /model command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['status'])
def handle_status_command(message):
    """Handle /status command - show current configuration."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /status command from chat {chat_id}")
    
    try:
        bot.send_chat_action(chat_id, 'typing')
        
        current_model = get_current_model(chat_id)
        current_project = get_current_project(chat_id)
        current_session = get_current_session_id(chat_id)
        
        response = "📋 Current Status:\n\n"
        response += "🤖 Model: " + (current_model if current_model else "Not set (using default)") + "\n"
        response += "📁 Project: " + (current_project if current_project else "Not set") + "\n"
        response += "🔀 Session: " + (current_session if current_session else "None (will create new)")
        
        escaped_message = escape_markdown_v2(response)
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /status command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['stats'])
def handle_stats_command(message):
    """Handle /stats command - show opencode usage statistics."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /stats command from chat {chat_id}")
    
    try:
        bot.send_chat_action(chat_id, 'typing')
        
        result = run_opencode_command(["stats"], timeout=10)
        stats_output = result.stdout
        
        escaped_message = escape_markdown_v2(f"📊 Opencode Statistics:\n\n{stats_output}")
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /stats command: {e}")
        escaped_error = escape_markdown_v2(f"Error fetching stats: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['history'])
def handle_history_command(message):
    """Handle /history command - show recent sessions."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /history command from chat {chat_id}")
    
    try:
        bot.send_chat_action(chat_id, 'typing')
        
        result = run_opencode_command(["session", "list", "--format", "json"])
        sessions = json.loads(result.stdout)
        
        if not sessions:
            escaped_message = escape_markdown_v2("No session history found.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            return
        
        # Sort by updated/created timestamp (most recent first)
        sorted_sessions = sorted(sessions, key=lambda x: x.get('updated', x.get('created', 0)), reverse=True)
        
        response = "📜 Recent Sessions (last 10):\n\n"
        current_session = get_current_session_id(chat_id)
        
        for idx, session in enumerate(sorted_sessions[:10], 1):
            session_id = session.get('id', 'Unknown')
            is_current = "✅" if session_id == current_session else "  "
            response += f"{is_current} {idx}. {session_id}\n"
        
        escaped_message = escape_markdown_v2(response)
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        
    except Exception as e:
        logger.error(f"Error handling /history command: {e}")
        escaped_error = escape_markdown_v2(f"Error fetching history: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['cancel'])
def handle_cancel_command(message):
    """Handle /cancel command - cancel current running command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /cancel command from chat {chat_id}")
    
    try:
        if chat_id in active_process:
            process = active_process[chat_id]
            if process.poll() is None:  # Process still running
                try:
                    process.terminate()
                    bot.reply_to(message, "❌ Command cancelled.", parse_mode="MarkdownV2")
                except ProcessLookupError:
                    bot.reply_to(message, "❌ Command already terminated.", parse_mode="MarkdownV2")
            else:
                bot.reply_to(message, "❌ No command is currently running.", parse_mode="MarkdownV2")
            del active_process[chat_id]
        else:
            bot.reply_to(message, "❌ No command is currently running.", parse_mode="MarkdownV2")
            
    except Exception as e:
        logger.error(f"Error handling /cancel command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    """Handle regular messages."""
    chat_id = str(message.chat.id)
    logger.info(f"Received message from chat {chat_id}: {message.text}")
    
    # Get current project path
    current_project = get_current_project(chat_id)
    
    # Get current model
    current_model = get_current_model(chat_id)
    
    # Build base command with project path if set
    base_args: List[str] = []
    if current_project:
        base_args.append(current_project)
    if current_model:
        base_args.append(f"--model={current_model}")
    base_args.append("run")
    
    # Check if we have an active session
    current_session_id = get_current_session_id(chat_id)
    
    if current_session_id:
        # Use the existing session
        logger.info(f"Using existing session {current_session_id}")
        command_args = base_args + ["--session", current_session_id, message.text, "--format", "json"]
        stream_opencode_output(chat_id, command_args)
    else:
        # Check if there are existing sessions to use instead of always creating a new one
        logger.info("No active session found, checking for existing sessions...")
        try:
            # First, get the list of existing sessions
            result = run_opencode_command(["session", "list", "--format", "json"])
            sessions_data = json.loads(result.stdout)
            
            if sessions_data:
                # Sort sessions by updated time (most recent first)
                # Note: This assumes sessions have a 'updated' or 'created' timestamp
                # If we don't have proper timestamp sorting, we'll use the last created session by default
                latest_session = max(sessions_data, key=lambda x: x.get('updated', x.get('created', 0)))
                selected_session_id = latest_session['id']
                
                logger.info(f"Using latest existing session {selected_session_id}")
                command_args = base_args + ["--session", selected_session_id, message.text, "--format", "json"]
                stream_opencode_output(chat_id, command_args)
            else:
                # No existing sessions, create a new one using --continue
                logger.info("No existing sessions, creating new session with --continue")
                command_args = base_args + ["--continue", message.text, "--format", "json"]
                
                # Execute the command, but just send a message to user to indicate it's running
                escaped_message = escape_markdown_v2("Executing command... Please wait.")
                bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
                
                stream_opencode_output(chat_id, command_args)
                
        except Exception as e:
            logger.error(f"Error checking existing sessions: {e}")
            # If we can't check sessions, fall back to creating a new one
            logger.info("Falling back to creating new session with --continue")
            command_args = base_args + ["--continue", message.text, "--format", "json"]
            
            escaped_message = escape_markdown_v2("Executing command... Please wait.")
            bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
            
            stream_opencode_output(chat_id, command_args)