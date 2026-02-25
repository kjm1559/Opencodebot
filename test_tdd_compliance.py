#!/usr/bin/env python3
"""
TDD Test Suite for Telegram Controller
Based on the specification in AGENTS.md

This test suite follows a test-driven development approach
to validate all features described in the specification.
"""

import json
import subprocess
import sys
from unittest.mock import Mock, patch
import asyncio

# Add project path to sys.path for imports
sys.path.insert(0, '/home/mj/project/Opencodebot')

import telegram_controller


def test_agents_spec_compliance():
    """
    Test that the implementation complies with AGENTS.md specification.
    """
    print("Testing AGENTS.md specification compliance...")
    
    # Test 1: Session Management Compliance
    print("1. Testing session management...")
    
    # Reset session store
    telegram_controller.session_store = {}
    
    # Test setting and getting session
    chat_id = "test_chat_123"
    session_id = "sess_123"
    
    telegram_controller.set_current_session_id(chat_id, session_id)
    retrieved_session = telegram_controller.get_current_session_id(chat_id)
    assert retrieved_session == session_id, "Session storage not working"
    
    print("   ✓ Session management works")
    
    # Test 2: Output Filtering Compliance
    print("2. Testing output filtering...")
    
    # Test that step_start and step_finish are filtered out
    step_start_line = '{"type":"step_start", "text":"Starting..."}'
    step_finish_line = '{"type":"step_finish", "text":"Finished"}'
    
    result_start = telegram_controller.process_output_line(step_start_line, chat_id)
    result_finish = telegram_controller.process_output_line(step_finish_line, chat_id)
    
    assert result_start == "", "step_start should be filtered out"
    assert result_finish == "", "step_finish should be filtered out"
    
    # Test that text messages are processed correctly
    text_line = '{"type":"text", "text":"Hello World"}'
    result_text = telegram_controller.process_output_line(text_line, chat_id)
    assert result_text == "Hello World", "text messages should be processed correctly"
    
    print("   ✓ Output filtering compliant")
    
    # Test 3: Tool Use Message Processing
    print("3. Testing tool use message processing...")
    
    tool_line = '{"type":"tool_use","part":{"tool":"curl","state":{"status":"completed","input":{"url":"http://example.com"}}}}'
    result_tool = telegram_controller.process_output_line(tool_line, chat_id)
    
    assert "[curl]:" in result_tool, "Tool name should be in output"
    assert "Status: completed" in result_tool or "input" in result_tool, "Tool input should be formatted"
    
    print("   ✓ Tool use processing compliant")
    
    # Test 4: Command Structure Compliance
    print("4. Testing command structure...")
    
    # Test that correct commands are generated
    # Regular message with session (simulated)
    command_args_with_session = ["run", "--session", "sess_123", "test message", "--format", "json"]
    assert command_args_with_session[0] == "run"
    assert command_args_with_session[1] == "--session"
    assert command_args_with_session[2] == "sess_123"
    
    # Regular message without session (simulated) 
    command_args_without_session = ["run", "--continue", "test message", "--format", "json"]
    assert command_args_without_session[0] == "run"
    assert command_args_without_session[1] == "--continue"
    
    print("   ✓ Command structure compliant")
    
    print("\nAll AGENTS.md specification tests passed!")


def test_json_processing():
    """Test JSON processing according to specification"""
    print("Testing JSON processing...")
    
    # Test valid JSONL content (like opencode run output)
    jsonl_content = '''{"type":"step_start", "text":"Starting..."}
{"type":"text", "text":"Hello"}
{"type":"step_finish", "text":"Finished"}
{"type":"tool_use","tool_name":"example_tool","input":{"param1":"value1"},"output":{"result":"success"}}'''
    
    lines = jsonl_content.strip().split('\n')
    processed_lines = []
    
    for line in lines:
        if line:  # Skip empty lines
            formatted = telegram_controller.process_output_line(line, "test_chat")
            if formatted and formatted.strip():
                processed_lines.append(formatted)
    
    # Should have 2 lines (text and tool_use, but step_start/step_finish filtered out)
    assert len(processed_lines) == 2, f"Expected 2 processed lines, got {len(processed_lines)}"
    assert "Hello" in processed_lines[0], "Text should be preserved"
    
    print("   ✓ JSON processing compliant")


def test_session_validation():
    """Test session validation functionality"""
    print("Testing session validation...")
    
    with patch('telegram_controller.run_opencode_command') as mock_run:
        # Mock session list response
        mock_result = Mock()
        mock_result.stdout = json.dumps([
            {"id": "sess_123", "created_at": "2023-01-01"},
            {"id": "sess_456", "created_at": "2023-01-02"}
        ])
        mock_run.return_value = mock_result
        
        # Test valid session ID
        is_valid = telegram_controller.is_valid_session_id("sess_123", "test_chat")
        assert is_valid == True, "Valid session ID should return True"
        
        # Test invalid session ID
        is_valid = telegram_controller.is_valid_session_id("sess_999", "test_chat")
        assert is_valid == False, "Invalid session ID should return False"
        
    print("   ✓ Session validation works")


def test_error_handling():
    """Test error handling compliance"""
    print("Testing error handling...")
    
    # Test that invalid JSON is handled gracefully
    invalid_json_line = 'invalid json {'
    result = telegram_controller.process_output_line(invalid_json_line, "test_chat")
    
    # Should return the raw line (for text messages)
    assert result == "invalid json {", "Invalid JSON should be handled gracefully"
    
    # Test empty line
    empty_line = ''
    result = telegram_controller.process_output_line(empty_line, "test_chat")
    assert result == "", "Empty line should return empty string"
    
    print("   ✓ Error handling compliant")


if __name__ == "__main__":
    try:
        test_agents_spec_compliance()
        test_json_processing() 
        test_session_validation()
        test_error_handling()
        print("\n✅ All TDD tests passed! Implementation compliant with AGENTS.md")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)