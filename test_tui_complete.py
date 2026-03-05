#!/usr/bin/env python3
"""TUI测试脚本"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试导入"""
    print("Testing TUI imports...")
    
    tests = [
        ("CodeAuditApp", "code_audit_agent.tui.app"),
        ("AppState", "code_audit_agent.tui.state"),
        ("AgentFlow", "code_audit_agent.tui.widgets.agent_flow"),
        ("LLMMessage", "code_audit_agent.tui.widgets.llm_message"),
        ("MessageLog", "code_audit_agent.tui.widgets.message_container"),
        ("HomeScreen", "code_audit_agent.tui.screens.home_screen"),
        ("AuditScreen", "code_audit_agent.tui.screens.audit_screen"),
        ("DirectoryBrowser", "code_audit_agent.tui.screens.directory_browser"),
        ("AuditRunner", "code_audit_agent.tui.utils.audit_runner"),
        ("InterruptibleLLMClient", "code_audit_agent.tui.utils.interruptible_llm"),
        ("AsyncWorker", "code_audit_agent.tui.utils.async_worker"),
    ]
    
    passed = 0
    failed = 0
    
    for name, module in tests:
        try:
            __import__(module, fromlist=[name])
            print(f"✓ {name} from {module}")
            passed += 1
        except Exception as e:
            print(f"✗ {name} from {module}: {e}")
            failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_state():
    """测试状态管理"""
    print("\nTesting AppState...")
    
    try:
        from code_audit_agent.tui.state import AppState
        
        # 测试单例模式
        state1 = AppState()
        state2 = AppState()
        
        assert state1 is state2, "AppState should be a singleton"
        print("✓ AppState singleton pattern works")
        
        # 测试添加Agent
        state1.add_agent("test_agent")
        assert "test_agent" in state1.agent_statuses, "Agent should be added"
        print("✓ Agent addition works")
        
        # 测试设置当前Agent
        state1.set_current_agent("test_agent")
        assert state1.current_agent == "test_agent", "Current agent should be set"
        print("✓ Current agent setting works")
        
        # 测试添加消息
        msg = state1.add_message("user", "test message", "test_agent")
        assert len(state1.llm_messages) == 1, "Message should be added"
        print("✓ Message addition works")
        
        # 测试重置
        state1.reset()
        assert len(state1.agent_statuses) == 0, "State should be reset"
        print("✓ State reset works")
        
        return True
    except Exception as e:
        print(f"✗ State test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_widgets():
    """测试组件"""
    print("\nTesting widgets...")
    
    try:
        from code_audit_agent.tui.widgets.llm_message import LLMMessage
        
        # 测试LLMMessage
        msg = LLMMessage(role="user", content="test")
        assert msg.role == "user", "Role should be user"
        assert msg.content == "test", "Content should be test"
        print("✓ LLMMessage creation works")
        
        # 测试标题生成
        assert "用户消息" in msg.title, "Title should contain user message"
        print("✓ Title generation works")
        
        return True
    except Exception as e:
        print(f"✗ Widget test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("TUI Application Test Suite")
    print("=" * 60)
    
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("State", test_state()))
    results.append(("Widgets", test_widgets()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✓ All tests passed!")
        return 0
    else:
        print("\n✗ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
