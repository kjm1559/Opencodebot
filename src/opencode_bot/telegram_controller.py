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
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
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

# Telegram MarkdownV2 escape function
def escape_markdown_v2(text: str) -> str:
    """Telegram MarkdownV2 escape function."""
    # Escape special characters for Telegram MarkdownV2 (in order: \ first!)
    result = text
    # Must escape \ first to avoid double-escaping
    result = result.replace('\\', '\\\\')
    # Then escape other special chars
    for char in r'_*$()~`>#+-=|{}.!':
        result = result.replace(char, f'\\{char}')
    return result

# Send startup message if TELEGRAM_CHAT_ID is set
def send_startup_message():
    """Send startup message to configured chat ID."""
    if TELEGRAM_CHAT_ID:
        try:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                escape_markdown_v2("🤖 Bot started!\nReady to accept commands."),
                parse_mode="MarkdownV2"
            )
            logger.info("Startup message sent")
        except Exception as e:
            logger.warning(f"Failed to send startup message: {e}")
    else:
        logger.info("TELEGRAM_CHAT_ID not set, skipping startup message")

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
        types.BotCommand("restart", "Restart bot (clears all sessions)"),
        types.BotCommand("project_list", "List workspace and root projects"),
        types.BotCommand("current_project", "Show current project"),
        types.BotCommand("workspace", "Set workspace project"),
        types.BotCommand("root", "Set project root"),
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

def escape_only_dots(text: str) -> str:
    """Escape special chars for Telegram MarkdownV2, skip ... pattern."""
    # Protect ... before escaping
    text = text.replace("...", "@@@")
    result = text.replace("\\", "\\\\")
    result = result.replace(".", r"\.").replace("-", r"\-").replace("(", r"\(").replace(")", r"\)").replace("_", r"\_").replace("#", r"\#").replace("!", r"\!").replace("=", r"\=").replace("+", r"\+")
    # Restore ... unchanged
    return result.replace("@@@", "...")

def collect_output_for_summary():
    """Initialize output collection."""
    return {"lines": [], "summary": None, "full_text": ""}

def process_line_for_summary(collect_data: dict, line: str, chat_id: Optional[str] = None) -> None:
    """Process a line and add to collection, extract session ID if found."""
    try:
        if not line:
            return
        obj = json.loads(line)
        
        if "lines" not in collect_data:
            collect_data["lines"] = []
        collect_data["lines"].append(obj)
        
        msg_type = obj.get("type", "")
        
        # Extract session ID from various locations
        if chat_id:
            # Try root level sessionID (camelCase)
            session_id = obj.get("sessionID")
            if not session_id:
                # Try root level session_id (snake_case)
                session_id = obj.get("session_id")
            if not session_id and "part" in obj:
                # Try part.sessionID
                part = obj.get("part", {})
                session_id = part.get("sessionID") or part.get("session_id")
            
            if session_id:
                set_current_session_id(chat_id, session_id)
                logger.info(f"Extracted session_id: {session_id}")
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
    
    message_lines = []
    detail_text = detail_text.strip() if detail_text else ""
    
    # Add AI response (brief preview)
    if summary["final_text"]:
        text = summary["final_text"].strip()
        preview_length = 800
        preview = text[:preview_length]
        
        message_lines.append("💬 AI Response:\n")
        message_lines.append(f"{preview}")
        
        if len(text) > preview_length:
            message_lines.append("\n\n... (truncated)")
            message_lines.append("\n👇 Click below for full response")
    
    # Activities summary
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
        message_lines.append("\n✨ Activities:")
        for item in emoji_parts:
            message_lines.append(f"\n  • {item}")
    
    return "".join(message_lines), detail_text

def process_output_line(line: str, chat_id: str) -> str:
    """Process a single line of opencode output and format it for Telegram."""
    try:
        if not line:
            return ""
        obj = json.loads(line)
        
        # Filter out step_start and step_finish messages completely
        if obj.get("type") == "step_start" or obj.get("type") == "step_finish":
            return ""
        
        msg_type = obj.get("type")
        
        if msg_type == "text":
            text_content = obj.get("text", "")
            part = obj.get("part", {})
            if part:
                text_content = part.get("text", text_content)
            return text_content.strip() or ""
            
        elif msg_type == "tool_use":
            tool_name = "Unknown tool"
            inputs = {}
            status = ""
            
            part = obj.get("part", {})
            if part:
                tool_name = part.get("tool", "Unknown tool")
                state = part.get("state", {})
                status = state.get("status", "")
                inputs = state.get("input", {})
            else:
                tool_name = obj.get("tool_name", obj.get("tool", "Unknown tool"))
                inputs = obj.get("input", {})
            
            result = f"[{tool_name}]:"
            if status:
                result += f"\n  Status: {status}"
            if inputs:
                result += f"\n  Input: {json.dumps(inputs, indent=2)}"
            return result.strip()
        
        else:
            return f"[{msg_type}]: {json.dumps(obj, indent=2)}"
            
    except json.JSONDecodeError as e:
        if "Extra data" in str(e):
            logger.warning(f"Skipping extra data in JSON: {line[:50]}")
            return ""
        logger.debug(f"JSON parse error: {e}")
        return line.strip() or ""

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

def get_action_message(tool: str, status: str, part: Optional[dict] = None) -> Optional[tuple]:
    """Get action message and full input detail for the tool and status.
    Returns: (message_to_send, full_detail_for_button) or None
    """
    if part is None:
        part = {}
    
    # Map tool names to action emoji and parameter keys (support both old and new formats)
    action_map = {
        "read": ("📖 Reading", ["filePath", "path", "file"]),
        "edit": ("✏️ Modifying", ["filePath", "path", "file"]),
        "write": ("📄 Writing", ["filePath", "path", "file"]),
        "bash": ("💻 Running", ["command"]),
        "webfetch": ("🌐 Fetching", ["url"]),
        "glob": ("🔍 Searching", ["pattern"]),
        "grep": ("🔍 Grep", ["pattern"]),
        "ast_grep": ("🔍 Searching", ["pattern"]),
        "skill": ("🔌 Using", ["name"]),
        "question": ("❓ Asking", ["questions"]),
    }
    
    # Normalize tool name
    base_tool = tool.split("_")[0] if "_" in tool else tool
    
    # Find matching action with param keys
    matched_action = None
    param_keys = []
    for key, (action, keys) in action_map.items():
        if key in base_tool or base_tool in key:
            matched_action = action
            param_keys = keys
            break
    
    if not matched_action:
        return None
    
    # Try to get input directly from state/input or inputs
    input_data = {}
    if "inputs" in part:
        input_data = part["inputs"]
    elif "state" in part and isinstance(part["state"], dict) and "input" in part["state"]:
        input_data = part["state"]["input"]
    
    # Try each parameter key in order
    value = None
    for key in param_keys:
        if input_data.get(key):
            value = input_data[key]
            break
    
    # Prepare short message (truncated)
    if value and isinstance(value, str):
        short_msg = value[:100] + "..." if len(value) > 100 else value
        return f"{matched_action}: {short_msg}", value
    elif input_data:
        # No specific param name, but have input - extract simplest meaningful value
        # Try to get a simple string from input data
        if isinstance(input_data, dict):
            # Find first simple string value
            for v in input_data.values():
                if isinstance(v, str) and len(v) < 500:
                    short_msg = v[:100] + "..." if len(v) > 100 else v
                    return f"{matched_action}: {short_msg}", v
        
        # Fall back to JSON if no simple value found
        json_str = json.dumps(input_data, indent=2)
        short_msg = json_str[:100] + "..." if len(json_str) > 100 else json_str
        return f"{matched_action}:\n```{short_msg}```", json_str
    
    return f"{matched_action}", None

def stream_opencode_output(chat_id: str, command_args: List[str]) -> None:
    """Stream opencode command output to terminal, send only summary to Telegram."""
    try:
        sent_messages = set()
        last_action = None
        
        logger.info(f"Executing opencode command with args: {command_args}")
        
        process = subprocess.Popen(
            ["opencode"] + command_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        active_process[chat_id] = process
        
        collect_data = collect_output_for_summary()
        
        # Stream stdout
        if process.stdout:
            for line in process.stdout:
                line = line.strip()
                if not line:
                    continue
                
                logger.debug("%s", line)
                process_line_for_summary(collect_data, line, chat_id)
                
                # Parse and send minimal status updates
                try:
                    obj = json.loads(line)
                    msg_type = obj.get("type", "")
                    
                    # Tool finished - send detailed action info
                    if msg_type == "tool_use":
                        part = obj.get("part", {})
                        tool = part.get("tool", "")
                        state = part.get("state", {})
                        status = state.get("status", "")
                        
                        logger.debug(f"Tool: {tool}, Status: {status}")
                        
                        result = get_action_message(tool, status, part)
                        # Send tool action for completed/started/success
                        if result and status in ("completed", "started", "success"):
                            action_msg, full_detail = result
                            
                            bot.send_chat_action(chat_id, 'typing')
                            escaped_msg = escape_markdown_v2(action_msg)
                            
                            try:
                                bot.send_message(chat_id, escaped_msg, parse_mode="MarkdownV2")
                                logger.info(f"✅ {tool}: {status}")
                            except Exception as e:
                                logger.error(f"Failed to send tool action: {e}")
                    
                    # Text output - send to Telegram
                    elif msg_type == "text":
                        text_content = obj.get("text", "")
                        part = obj.get("part", {})
                        if part:
                            text_content = part.get("text", text_content)
                        
                        if text_content.strip():
                            # Truncate very long text
                            display_text = text_content.strip()[:300] + "..." if len(text_content.strip()) > 300 else text_content.strip()
                            bot.send_chat_action(chat_id, 'typing')
                            try:
                                bot.send_message(chat_id, escape_markdown_v2(display_text), parse_mode="MarkdownV2")
                                logger.info(f"📝 Text output sent ({len(text_content)} chars)")
                            except Exception as e:
                                logger.warning(f"Failed to send text output: {e}")
                    
                    # Session started - show session ID
                    elif msg_type == "session_started":
                        session_id = obj.get("session_id", "")
                        if session_id:
                            msg = f"📝 Session: {session_id[:12]}..."
                            if msg not in sent_messages:
                                sent_messages.add(msg)
                                bot.send_chat_action(chat_id, 'typing')
                                try:
                                    bot.send_message(chat_id, escape_markdown_v2(msg), parse_mode="MarkdownV2")
                                    logger.info(f"🚀 Session started: {session_id}")
                                except Exception as e:
                                    logger.warning(f"Failed to send session start: {e}")
                    
                    # Step finished with summary - indicate completion
                    elif msg_type == "step_finish":
                        step = obj.get("step", -1)
                        if step > 0:
                            msg = f"✅ Step {step} completed"
                            if msg not in sent_messages:
                                sent_messages.add(msg)
                                try:
                                    bot.send_chat_action(chat_id, 'typing')
                                    bot.send_message(chat_id, escape_markdown_v2(msg), parse_mode="MarkdownV2")
                                except Exception:
                                    pass
                    
                    # Error - notify immediately
                    elif msg_type == "error":
                        error_msg = obj.get("text", "") or obj.get("message", "")
                        if error_msg:
                            error_preview = error_msg[:100] + "..." if len(error_msg) > 100 else error_msg
                            msg = f"⚠️ Error: {error_preview}"
                            if msg not in sent_messages:
                                sent_messages.add(msg)
                                try:
                                    bot.send_chat_action(chat_id, 'typing')
                                    bot.send_message(chat_id, escape_markdown_v2(msg), parse_mode="MarkdownV2")
                                except Exception as e:
                                    logger.warning(f"Failed to send error: {e}")
                    
                except json.JSONDecodeError:
                    pass
        
        # Stream stderr
        if process.stderr:
            for line in process.stderr:
                logger.error("STDERR: %s", line.strip())
        
        return_code = process.wait()
        if return_code != 0:
            logger.error(f"opencode command exited with code {return_code}")
        
        # Generate and send summary
        summary = summarize_output(collect_data.get("lines", []))
        full_text = summary.get("final_text", "")
        
        logger.info(f"Summary: {summary}")
        
        summary_text, detail_text = format_summary_message(summary, full_text)
        if not summary_text.strip():
            summary_text = "✅ Completed"
        
        escaped_summary = escape_only_dots(summary_text)
        
        try:
            # Send typing before summary
            bot.send_chat_action(chat_id, 'typing')
            bot.send_message(
                chat_id,
                f"📊 Summary:\n\n{escaped_summary}",
                parse_mode="MarkdownV2"
            )
            
            # Send full detail in chunks if available
            if detail_text and len(detail_text) > 1000:
                logger.info(f"Sending full details ({len(detail_text)} chars)")
                
                # Telegram message limit is 4096 characters
                chunk_size = 3500
                chunks = [detail_text[i:i+chunk_size] for i in range(0, len(detail_text), chunk_size)]
                
                for idx, chunk in enumerate(chunks, 1):
                    if idx == 1:
                        chunk_msg = f"📋 Full Details:\n\n{escape_markdown_v2(chunk)}"
                    else:
                        chunk_msg = f"📋 Full Details (cont.) #{idx}:\n\n{escape_markdown_v2(chunk)}"
                    
                    # Send typing before each detail chunk
                    bot.send_chat_action(chat_id, 'typing')
                    bot.send_message(chat_id, chunk_msg, parse_mode="MarkdownV2")
                    logger.info(f"Sent detail chunk {idx}/{len(chunks)}")
            
            logger.info("Summary sent successfully")
        except Exception as e:
            logger.error(f"Error sending summary: {e}")
            try:
                bot.send_chat_action(chat_id, 'typing')
                bot.send_message(chat_id, f"📊 Summary:\n{escape_markdown_v2(summary_text)}", parse_mode="MarkdownV2")
            except Exception as e2:
                logger.error(f"Error sending plain summary: {e2}")
        
        # Send completion message (this will stop typing indicator)
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
    """Handle /project command - list workspace projects, switch, or clone."""
    chat_id = str(message.chat.id)
    project_input = message.text[len('/project'):].strip()
    
    # Get current project first (needed for workspace path)
    current_project = get_current_project(chat_id)
    if not current_project:
        current_project = "."
    current_project = os.path.expanduser(current_project)
    workspace_dir = os.path.join(current_project, "workspace")
    
    # Handle git URL (clone project)
    if project_input.startswith(('git@', 'http://', 'https://', 'git://')):
        bot.send_message(chat_id, escape_markdown_v2("🔄 Cloning..."), parse_mode="MarkdownV2")
        
        try:
            repo_name = project_input.split('/')[-1].replace('.git', '')
            clone_path = os.path.join(workspace_dir, repo_name)
            os.makedirs(workspace_dir, exist_ok=True)
            
            result = subprocess.run(
                ['git', 'clone', project_input, clone_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                bot.reply_to(message, escape_markdown_v2(f"❌ Clone failed: {result.stderr}"), parse_mode="MarkdownV2")
                return
            
            # Set the cloned project as current
            set_current_project(chat_id, clone_path)
            
            # Create a new session for this project
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
    
    if not project_input:
        # List workspace projects
        workspace_projects = []
        
        if os.path.exists(workspace_dir) and os.path.isdir(workspace_dir):
            for item in os.listdir(workspace_dir):
                item_path = os.path.join(workspace_dir, item)
                git_path = os.path.join(item_path, ".git")
                if os.path.isdir(item_path) and (os.path.isfile(git_path) or os.path.isdir(git_path)):
                    workspace_projects.append(item)
        
        response = "📁 Workspace Projects:\n\n"
        
        if not workspace_projects:
            response += "(No projects in workspace)\n\n"
        else:
            for i, proj in enumerate(sorted(workspace_projects), 1):
                marker = "✅" if current_project and proj in str(current_project) else " "
                response += f"{marker} {i}. {proj}\n"
        
        if current_project:
            response += f"\n📍 Current: {os.path.basename(str(current_project))}"
        else:
            response += "\n📍 No project selected"
        
        response += "\n\n💡 Use /project \u003cgit-url\u003e to clone a project"
        
        bot.reply_to(message, escape_markdown_v2(response), parse_mode="MarkdownV2")
        return
    
    # Handle project number
    workspace_projects = []
    if os.path.exists(workspace_dir) and os.path.isdir(workspace_dir):
        for item in os.listdir(workspace_dir):
            item_path = os.path.join(workspace_dir, item)
            if os.path.isdir(item_path):
                workspace_projects.append(item)
    
    if project_input.isdigit():
        idx = int(project_input) - 1
        
        if 0 <= idx < len(workspace_projects):
            selected_project = workspace_projects[idx]
            project_path = os.path.join(workspace_dir, selected_project)
            set_current_project(chat_id, project_path)
            bot.reply_to(
                message,
                escape_markdown_v2(f"📁 Switched to: {selected_project}\n🔄 Session preserved"),
                parse_mode="MarkdownV2"
            )
        else:
            bot.reply_to(message, escape_markdown_v2("❌ Invalid project number"), parse_mode="MarkdownV2")
        return
    
    # Handle project name (in workspace)
    project_path = os.path.join(workspace_dir, project_input)
    if os.path.exists(project_path) and os.path.isdir(project_path):
        set_current_project(chat_id, project_path)
        bot.reply_to(
            message,
            escape_markdown_v2(f"📁 Switched to: {project_input}\n🔄 Session preserved"),
            parse_mode="MarkdownV2"
        )
    else:
        bot.reply_to(message, escape_markdown_v2(f"❌ Not found: {project_input}"), parse_mode="MarkdownV2")

@bot.message_handler(commands=['project_list'])
def handle_project_list_command(message):
    """Handle /project_list command - show workspace and root directories."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /project_list command from chat {chat_id}")
    
    try:
        project_input = message.text[len('/project_list'):].strip()
        
        # Get current project path
        current_project = get_current_project(chat_id)
        if not current_project:
            current_project = "."  # Default to current directory
        
        current_project = os.path.expanduser(current_project)
        
        response = "📁 Project List:\n\n"
        
        # Show workspace directory if it exists
        workspace_dir = os.path.join(current_project, "workspace")
        if os.path.exists(workspace_dir) and os.path.isdir(workspace_dir):
            response += "📓 Workspace Projects:\n"
            workspace_items = []
            for item in os.listdir(workspace_dir):
                item_path = os.path.join(workspace_dir, item)
                if os.path.isdir(item_path):
                    # Check if it's a git repo
                    if os.path.exists(os.path.join(item_path, ".git")):
                        marker = "✅" if current_project and item_path in str(current_project) else " "
                        workspace_items.append((marker, item))
            
            if workspace_items:
                for marker, item in sorted(workspace_items):
                    response += f"  {marker} {item}\n"
            else:
                response += "  (empty)\n"
            response += "\n"
        
        # Show root directory option
        response += "📁 Root:\n"
        marker = "✅" if current_project and os.path.abspath(current_project) in os.path.abspath(current_project) else " "
        response += f"  {marker} . (current project root: {os.path.basename(os.path.abspath(current_project))})\n\n"
        
        # Instructions
        response += "\n📝 Instructions:\n"
        response += "  Use /workspace <workspace-name> to set a workspace project\n"
        response += "  Use /root to set the current project root\n"
        
        # Handle project selection via argument
        if project_input:
            if project_input == "root" or project_input == ".":
                # Set to current root
                set_current_project(chat_id, os.path.abspath(current_project))
                bot.reply_to(
                    message,
                    escape_markdown_v2(f"📁 Set to project root: {os.path.abspath(current_project)}"),
                    parse_mode="MarkdownV2"
                )
                return
            
            # Try to find in workspace
            if os.path.exists(workspace_dir):
                workspace_path = os.path.join(workspace_dir, project_input)
                if os.path.exists(workspace_path):
                    set_current_project(chat_id, workspace_path)
                    bot.reply_to(
                        message,
                        escape_markdown_v2(f"📁 Set workspace project: {project_input}"),
                        parse_mode="MarkdownV2"
                    )
                    return
        
        escaped_response = escape_markdown_v2(response)
        bot.reply_to(message, escaped_response, parse_mode="MarkdownV2")
    
    except Exception as e:
        logger.error(f"Error handling /project_list command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['root'])
def handle_root_command(message):
    """Handle /root command - set to project root."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /root command from chat {chat_id}")
    
    try:
        # Get current project path
        current_project = get_current_project(chat_id)
        
        if current_project:
            root_path = os.path.abspath(os.path.expanduser(current_project))
            set_current_project(chat_id, root_path)
            bot.reply_to(
                message,
                escape_markdown_v2(f"📁 Set to project root:\n{root_path}"),
                parse_mode="MarkdownV2"
            )
        else:
            bot.reply_to(
                message,
                escape_markdown_v2("❌ No project set.\n\nUse /project_list to see available projects."),
                parse_mode="MarkdownV2"
            )
    
    except Exception as e:
        logger.error(f"Error handling /root command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['workspace'])
def handle_workspace_command(message):
    """Handle /workspace command - set workspace project."""
    chat_id = str(message.chat.id)
    workspace_name = message.text[len('/workspace'):].strip()
    logger.info(f"Received /workspace command for {workspace_name} from chat {chat_id}")
    
    try:
        if not workspace_name:
            bot.reply_to(
                message,
                escape_markdown_v2("❌ Please provide workspace name.\n\nUsage: /workspace <workspace-name>"),
                parse_mode="MarkdownV2"
            )
            return
        
        # Get current project path
        current_project = get_current_project(chat_id)
        if not current_project:
            current_project = "."
        
        workspace_dir = os.path.join(os.path.expanduser(current_project), "workspace")
        workspace_path = os.path.join(workspace_dir, workspace_name)
        
        if os.path.exists(workspace_path):
            set_current_project(chat_id, workspace_path)
            bot.reply_to(
                message,
                escape_markdown_v2(f"📁 Set workspace project: {workspace_name}"),
                parse_mode="MarkdownV2"
            )
        else:
            bot.reply_to(
                message,
                escape_markdown_v2(f"❌ Workspace not found: {workspace_name}\n\nUse /project_list to see available workspaces."),
                parse_mode="MarkdownV2"
            )
    
    except Exception as e:
        logger.error(f"Error handling /workspace command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

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
            "/project_list - List workspace and root projects\n"
            "/workspace <name> - Set workspace project\n"
            "/root - Set project root\n"
            "/current_project - Show current project\n"
            "/model [name] - List/set current model\n"
            "/session - List available sessions\n"
            "/set_session <id> - Set current session\n"
            "/current_session - Show current session\n"
            "/new_session - Create new session\n"
            "/compact <session_id> - Compact current session\n"
            "/reset - Clear current session (creates new on next command)\n"
            "/restart - Restart bot (clears all sessions)\n"
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

@bot.message_handler(commands=['current_project'])
def handle_current_project_command(message):
    """Handle /current_project command - show current project."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /current_project command from chat {chat_id}")
    
    try:
        current_project = get_current_project(chat_id)
        
        if current_project:
            escaped_message = escape_markdown_v2(f"📁 Current Project:\n{current_project}")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        else:
            escaped_message = escape_markdown_v2("📁 No current project set.\n\nUse /project to list and select projects.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
    
    except Exception as e:
        logger.error(f"Error handling /current_project command: {e}")
        escaped_error = escape_markdown_v2(f"Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['current_session'])
def handle_current_session_command(message):
    """Handle /current_session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /current_session command from chat {chat_id}")
    
    try:
        # First check in-memory store
        session_id = get_current_session_id(chat_id)
        
        if not session_id:
            session_id = None
            try:
                result = run_opencode_command(["session", "list", "--format", "json"])
                sessions_data = json.loads(result.stdout)
                
                if sessions_data and isinstance(sessions_data, list):
                    latest_session = max(sessions_data, key=lambda x: x.get('updated', x.get('created', 0)))
                    session_id = latest_session.get('id', '')
                    if session_id:
                        logger.info(f"Auto-detected latest session: {session_id}")
                else:
                    logger.warning("Session list is empty or not a list")
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse session list JSON: {e}")
            except (KeyError, ValueError) as e:
                logger.error(f"Error getting latest session: {e}")
        
        if session_id:
            escaped_message = escape_markdown_v2(f"📝 Current session: {session_id}")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        else:
            escaped_message = escape_markdown_v2("❌ No active session.\n\nUse /new_session to create one.")
            bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"opencode command failed in /current_session: {e}")
        escaped_error = escape_markdown_v2("❌ Failed to query sessions. Please check opencode status.")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")
    except Exception as e:
        logger.error(f"Unexpected error in /current_session: {e}")
        escaped_error = escape_markdown_v2(f"❌ Error: {str(e)}")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")

@bot.message_handler(commands=['new_session'])
def handle_new_session_command(message):
    """Handle /new_session command."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /new_session command from chat {chat_id}")
    
    try:
        # Show typing indicator
        bot.send_chat_action(chat_id, 'typing')
        
        # Clear the current session for this chat
        session_id = get_current_session_id(chat_id)
        if session_id:
            logger.info(f"Cleared current session: {session_id}")
        
        # Clear session from store - next command will create a new session automatically
        set_current_session_id(chat_id, "")
        
        escaped_message = escape_markdown_v2("✅ Session cleared.\n\n💡 Your next command will create a new session automatically.")
        bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
        logger.info(f"Cleared session for chat {chat_id}")
                
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
        # First check in-memory store
        session_id = get_current_session_id(chat_id)
        
        # If not found or empty, get latest from opencode
        if not session_id:
            result = run_opencode_command(["session", "list", "--format", "json"])
            sessions_data = json.loads(result.stdout)
            if sessions_data:
                # Sort by updated timestamp (most recent first)
                latest_session = max(sessions_data, key=lambda x: x.get('updated', x.get('created', 0)))
                session_id = latest_session['id']
                set_current_session_id(chat_id, session_id)  # Cache it
                logger.info(f"Auto-detected latest session for compact: {session_id}")
            else:
                escaped_message = escape_markdown_v2("No sessions available to compact.")
                bot.reply_to(message, escaped_message, parse_mode="MarkdownV2")
                return
            
        # Compact the session
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

@bot.message_handler(commands=['restart'])
def handle_restart_command(message):
    """Handle /restart command - restart the bot."""
    chat_id = str(message.chat.id)
    logger.info(f"Received /restart command from chat {chat_id}")
    
    try:
        # Cancel any running process
        if chat_id in active_process:
            try:
                active_process[chat_id].terminate()
                del active_process[chat_id]
            except Exception:
                pass
        
        bot.reply_to(message, escape_markdown_v2("🔄 Restarting bot..."), parse_mode="MarkdownV2")
        
        # Clear all sessions
        session_store.clear()
        logger.info("Cleared all sessions")
        
        # Wait a moment then restart
        import time
        time.sleep(2)
        
        # Kill and restart the process
        import os
        logger.info("Restarting with: python main.py")
        os.execv(sys.executable, [sys.executable, "main.py"])
        
    except Exception as e:
        logger.error(f"Error handling /restart command: {e}")
        escaped_error = escape_markdown_v2(f"❌ Failed to restart: {str(e)}\n\nPlease restart manually.")
        bot.reply_to(message, escaped_error, parse_mode="MarkdownV2")
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
    
    # Build base command
    base_args = ["run", message.text, "--format", "json"]
    
    # Add project directory
    if current_project:
        base_args.extend(["--dir", current_project])
    
    # Add model
    if current_model:
        base_args.extend(["--model", current_model])
    
    # Check if we have an active session
    current_session_id = get_current_session_id(chat_id)
    
    if current_session_id:
        # Use the existing session
        logger.info(f"Using existing session {current_session_id}")
        command_args = base_args + ["--session", current_session_id]
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
                latest_session = max(sessions_data, key=lambda x: x.get('updated', x.get('created', 0)))
                selected_session_id = latest_session['id']
                
                logger.info(f"Using latest existing session {selected_session_id}")
                command_args = base_args + ["--session", selected_session_id]
                stream_opencode_output(chat_id, command_args)
            else:
                # No existing sessions, create a new one using --continue
                logger.info("No existing sessions, creating new session with --continue")
                command_args = base_args + ["--continue"]
                
                # Execute the command, but just send a message to user to indicate it's running
                escaped_message = escape_markdown_v2("Executing command... Please wait.")
                bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
                
                stream_opencode_output(chat_id, command_args)
                
        except Exception as e:
            logger.error(f"Error checking existing sessions: {e}")
            # If we can't check sessions, fall back to creating a new one
            logger.info("Falling back to creating new session with --continue")
            command_args = base_args + ["--continue"]
            
            escaped_message = escape_markdown_v2("Executing command... Please wait.")
            bot.send_message(chat_id, escaped_message, parse_mode="MarkdownV2")
            
            stream_opencode_output(chat_id, command_args)