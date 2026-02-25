#!/usr/bin/env python3
"""
Test file for Telegram Controller using pytest framework.
This implements the TDD approach for the Telegram controller.
"""

import json
import sys
from unittest.mock import Mock, patch

# Add project path to sys.path for imports
sys.path.insert(0, '/home/mj/project/Opencodebot')

import telegram_controller

def test_process_output_line_text_type():
    """Test processing of text type output lines"""
    # Test basic text message
    line = '{"type":"text","text":"Hello World"}'
    result = telegram_controller.process_output_line(line, "test_chat")
    assert result == "Hello World"
    
    # Test text with nested part structure
    line = '{"type":"text","part":{"text":"Nested text"}}'
    result = telegram_controller.process_output_line(line, "test_chat")
    assert result == "Nested text"

def test_process_output_line_tool_use_type():
    """Test processing of tool_use type output lines"""
    # Test tool use with nested structure
    line = '{"type":"tool_use","part":{"tool":"example_tool","state":{"status":"success","input":{"param1":"value1"},"output":{"result":"success"}}}}'
    result = telegram_controller.process_output_line(line, "test_chat")
    
    assert "[example_tool]:" in result
    assert "Status: success" in result
    assert '"param1": "value1"' in result

def test_process_output_line_step_filtering():
    """Test that step_start and step_finish messages are filtered out"""
    # Test step_start filtering
    line = '{"type":"step_start","text":"Starting..."}'
    result = telegram_controller.process_output_line(line, "test_chat")
    assert result == ""
    
    # Test step_finish filtering
    line = '{"type":"step_finish","text":"Finished"}'
    result = telegram_controller.process_output_line(line, "test_chat")
    assert result == ""

def test_format_session_list():
    """Test formatting session list for Telegram"""
    sessions = [
        {"id": "sess_123", "created_at": "2023-01-01"},
        {"id": "sess_456", "created_at": "2023-01-02"}
    ]
    result = telegram_controller.format_session_list(sessions)
    
    assert "Available Sessions:" in result
    assert "- sess_123" in result
    assert "- sess_456" in result

def test_format_session_list_empty():
    """Test formatting empty session list"""
    result = telegram_controller.format_session_list([])
    assert result == "No sessions available."

def test_session_storage_operations():
    """Test session storage operations"""
    # Reset storage
    telegram_controller.session_store = {}
    
    chat_id = "test_chat_123"
    session_id = "test_session_456"
    
    # Set session
    telegram_controller.set_current_session_id(chat_id, session_id)
    
    # Retrieve session
    result = telegram_controller.get_current_session_id(chat_id)
    assert result == session_id
    
    # Test non-existent session
    result = telegram_controller.get_current_session_id("nonexistent_chat")
    assert result is None

def test_is_valid_session_id():
    """Test session ID validation"""
    # Mock the subprocess call to return valid sessions
    with patch('telegram_controller.run_opencode_command') as mock_run:
        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {"id": "sess_123", "created_at": "2023-01-01"},
            {"id": "sess_456", "created_at": "2023-01-02"}
        ])
        mock_run.return_value = mock_result
        
        # Test with a valid session ID
        result = telegram_controller.is_valid_session_id("sess_123", "test_chat")
        assert result == True
        
        # Test with an invalid session ID
        result = telegram_controller.is_valid_session_id("sess_999", "test_chat")
        assert result == False

def test_escape_md():
    """Test markdown escaping function"""
    # Test special characters
    test_text = "*bold* _italic_ [link](url) `code`"
    result = telegram_controller.escape_md(test_text)
    
    # Check that special characters are escaped
    assert result == "\\*bold\\* \\_italic\\_ \\[link\\](url) \\`code\\`"

def test_run_opencode_command():
    """Test running opencode command successfully"""
    with patch('subprocess.run') as mock_run:
        mock_result = Mock()
        mock_result.stdout = '{"id": "test_session", "created_at": "2023-01-01"}'
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = telegram_controller.run_opencode_command(["session", "list"])
        
        assert result.stdout == '{"id": "test_session", "created_at": "2023-01-01"}'

if __name__ == "__main__":
    # Run tests if file is executed directly
    import pytest
    pytest.main([__file__, "-v"])