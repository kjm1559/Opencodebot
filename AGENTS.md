# AGENTS.md

## Project: Telegram Controller for OpenCode

### Overview

This document defines the architecture and behavior of a Telegram bot that controls `opencode` via CLI.

The bot must:

- Manage OpenCode sessions via Telegram commands
- Execute `opencode run` commands
- Parse JSON / JSONL outputs
- Stream filtered results back to Telegram
- Automatically manage and track the current session

This document serves as the implementation guide for building the system.

---

# 1. High-Level Architecture

## Components

1. **Telegram Bot Layer**
   - Handles commands and user messages
   - Sends responses back to Telegram

2. **Session Manager**
   - Stores and retrieves `current_session_id`
   - Interfaces with `opencode session list`

3. **OpenCode CLI Adapter**
   - Executes CLI commands:
     - `opencode session list --format json`
     - `opencode run --session ... --format json`
     - `opencode run --continue ... --format json`
   - Parses JSON and JSONL outputs

4. **Output Processor**
   - Filters out:
     - `type == "step_start"`
     - `type == "step_finish"`
   - Forwards remaining entries to Telegram

---

# 2. Session Management

Session state must be maintained per Telegram chat (recommended) or globally (if single-user bot).

## Stored State

```json
{
  "current_session_id": "string | null"
}
```
# 3. Telegram Commands

## 3.1 /session

### Behavior
1. Execute:
```bash
opencode session list --format json
```
2. Parse stdout JSON.
3. Extract only id fields.
4. Send list of session IDs to Telegram.

### Expected JSON Format (Example)
```json
[
  {
    "id": "sess_123",
    "created_at": "...",
    ...
  },
  {
    "id": "sess_456"
  }
]
```

### Telegram Output Example
```
Available Sessions:
- sess_123
- sess_456
```

## 3.2 /set_session <session_id>

### Behavior
- Store provided session_id as current_session_id
- Validate optionally against session list
- Reply:
```
Current session set to: sess_123
```

## 3.3 /current_session

### Behavior
- Return stored current_session_id
- If none:
```
No active session.
```

# 4. Message Handling Flow

When a user sends a normal message (non-command):

## 4.1 If current_session_id exists

Execute:
```bash
opencode run --session "<session_id>" "<user_message>" --format json
```

## 4.2 If current_session_id does NOT exist
1. Execute:
```bash
opencode run --continue "<user_message>" --format json
```
2. Immediately after execution completes, run:
```bash
opencode session list --format json
```
3. Parse JSON.
4. Retrieve the most recently created session.
5. Set its id as current_session_id.

# 5. Handling opencode run Output

### Output Format

opencode run produces JSONL (JSON per line).

Example:
```json
{"type":"step_start", ...}
{"type":"text","text":"Hello"}
{"type":"step_finish", ...}
{"type":"tool_use","tool_name":"example_tool","input":{"param1":"value1"},"output":{"result":"success"}}
```

### Filtering Rules

DO NOT send entries where:
- type == "step_start"
- type == "step_finish"

Send everything else to Telegram.

### Processing Rules

- `type == "text"`: Send only the text content (not the full JSON object)
- `type == "tool_use"`: Send tool name, inputs, and outputs in structured format
- Other types: Send formatted JSON representation

### Processing Algorithm

Pseudo-code:

```python
for line in stdout_stream:
    obj = json.loads(line)

    if obj["type"] in ["step_start", "step_finish"]:
        continue

    send_to_telegram(format_message(obj))
```

### Error Handling

In case of asynchronous execution errors:
- Handle coroutine execution properly in message handlers
- Ensure stream_opencode_output is called without incorrect asyncio.run() calls

### Filtering Rules

DO NOT send entries where:
- type == "step_start"
- type == "step_finish"

Send everything else to Telegram.

### Processing Rules

- `type == "text"`: Send only the text content (not the full JSON object)
- `type == "tool_use"`: Send tool name, inputs, and outputs in structured format
- Other types: Send formatted JSON representation

### Processing Algorithm

Pseudo-code:

```python
for line in stdout_stream:
    obj = json.loads(line)

    if obj["type"] in ["step_start", "step_finish"]:
        continue

    send_to_telegram(format_message(obj))
```

# 6. Detailed Execution Flow

### Message Processing Sequence
```
User Message →
Check current_session_id →
    YES → opencode run --session
    NO  → opencode run --continue
              ↓
         session list
              ↓
         set latest session_id
              ↓
Stream output →
Filter →
Send to Telegram
```

### 7. Extracting Latest Session

After:
```bash
opencode session list --format json
```

Assume response sorted by update time ascending or descending.

If ascending:
- Use last element.

If descending:
- Use first element.

Implementation must confirm actual ordering behavior.

```python
sessions = json.loads(stdout)

latest = sorted(
    sessions,
    key=lambda s: s["updated"]
)[-1]

current_session_id = latest["id"]
```

# 8. Error Handling

### CLI Failure

If subprocess exits non-zero:
- Capture stderr
- Send error message to Telegram:
```
Error executing opencode:
<stderr output>
```

### Invalid Session ID

If /set_session receives invalid ID:
- Optionally validate via session list
- Return:
```
Invalid session ID.
```

# 9. Concurrency Considerations
- If multi-user bot:
    - Store session per chat_id
- If single-user:
    - Global in-memory storage sufficient

Recommended structure:
```python
session_store = {
    chat_id: {
        "current_session_id": "sess_123"
    }
}
```

# 10. Implementation Requirements
- Must use subprocess streaming (not blocking full capture)
- Must support large outputs
- Must safely escape user input
- Must ensure proper JSON parsing
- Must gracefully handle malformed JSON lines

# 11. Example Command Summary

| Telegram Input | CLI Command |
|----------------|------------|
| `/session` | `opencode session list --format json` |
| `/set_session sess_123` | (Store session internally only) |
| `/current_session` | (Read current session internally) |
| Normal message (with session) | `opencode run --session "sess_123" "message" --format json` |
| Normal message (no session) | `opencode run --continue "message" --format json` → `opencode session list --format json` → set latest session as current |

# 12. Future Extensions (Optional)
- /new_session
- /delete_session
- Streaming partial responses
- Inline session selection buttons
- Persistent DB-backed session storage

# 13. Implementation Notes
- All commands and message types from specification have been implemented
- Session storage is in-memory (per chat) - for production use, implement database-backed storage
- Environment variables TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are supported
- User feedback "Executing command... Please wait." is shown during command execution
- All filtering rules from specification are implemented (step_start/step_finish messages filtered out)
- Tool_use messages are formatted with tool name, inputs, and outputs as specified
- Tool_use messages display in format: [tool_name]:\nInput: {input_data}\nOutput: {output_data}\n with code block formatting
- Text messages are displayed verbatim as received from opencode
- Each opencode output line is sent as a single message to Telegram

⸻

End of AGENTS.md
