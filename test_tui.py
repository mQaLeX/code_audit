"""TUI测试脚本"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from code_audit_agent.tui.app import CodeAuditApp


def test_import():
    """测试导入"""
    print("Testing TUI imports...")
    
    try:
        from code_audit_agent.tui.app import CodeAuditApp
        print("✓ CodeAuditApp imported successfully")
    except Exception as e:
        print(f"✗ Failed to import CodeAuditApp: {e}")
        return False
    
    try:
        from code_audit_agent.tui.state import AppState
        print("✓ AppState imported successfully")
    except Exception as e:
        print(f"✗ Failed to import AppState: {e}")
        return False
    
    try:
        from code_audit_agent.tui.widgets.agent_flow import AgentFlow
        print("✓ AgentFlow imported successfully")
    except Exception as e:
        print(f"✗ Failed to import AgentFlow: {e}")
        return False
    
    try:
        from code_audit_agent.tui.widgets.llm_message import LLMMessage
        print("✓ LLMMessage imported successfully")
    except Exception as e:
        print(f"✗ Failed to import LLMMessage: {e}")
        return False
    
    try:
        from code_audit_agent.tui.widgets.message_container import MessageLog
        print("✓ MessageLog imported successfully")
    except Exception as e:
        print(f"✗ Failed to import MessageLog: {e}")
        return False
    
    try:
        from code_audit_agent.tui.screens.home_screen import HomeScreen
        print("✓ HomeScreen imported successfully")
    except Exception as e:
        print(f"✗ Failed to import HomeScreen: {e}")
        return False
    
    try:
        from code_audit_agent.tui.screens.audit_screen import AuditScreen
        print("✓ AuditScreen imported successfully")
    except Exception as e:
        print(f"✗ Failed to import AuditScreen: {e}")
        return False
    
    print("\nAll imports successful!")
    return True


if __name__ == "__main__":
    test_import()
