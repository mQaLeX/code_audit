"""审计界面"""

from textual.screen import Screen
from textual.widgets import Static, Button, Input, Checkbox, Label, TextArea
from textual.containers import Container, Vertical, Horizontal
from textual.message import Message
from typing import Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from code_audit_agent.tui.widgets.agent_flow import AgentFlow
from code_audit_agent.tui.widgets.message_container import MessageLog
from code_audit_agent.tui.state import AppState


class AuditScreen(Screen):
    """审计界面"""
    CSS = """
    #bottom_input {
        height: auto;
        margin: 1;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }

    #bottom_input TextArea {
        # width: auto; 
        min-width: 20; 
        margin-right: 1;
        overflow: auto;
        min-height: 3;
        max-height: 10;
    }
    
    #messages_log{
        height: 1fr;
        min-height: 20;
    }
    """
    
    class InterruptRequest(Message):
        """请求用户输入介入"""
        def __init__(self, prompt: str):
            self.prompt = prompt
            super().__init__()
    
    def __init__(self):
        super().__init__()
        self.app_state = AppState()
        self.interrupt_mode = False
        self.current_input: Optional[str] = None
        self.is_receiving_response = False
    
    def compose(self) -> None:
        """组成界面"""
        yield Static("代码审计AI Agent - 审计中", id="audit_title")
        
        with Vertical(id="main_content"):
            # Agent流程可视化
            yield AgentFlow(
                agents=["scanner", "trace_agent", "audit_agent", "exploit_agent", "report_agent"],
                id="agent_flow"
            )
            
            # 消息日志
            yield Static("LLM对话", id="messages_label")
            yield MessageLog(id="messages_log")
            
            # 底部输入区域
            with Horizontal(id="bottom_input"):
                yield TextArea(placeholder="输入消息...", id="user_input")
                yield Checkbox("干扰模式", id="interrupt_checkbox")
                yield Button("发送", id="send_button")
        
        yield Static("按 Ctrl+C 退出", id="footer")
    
    def on_mount(self) -> None:
        """挂载时初始化"""
        self.app_state.reset()
        
        # 初始化Agent状态
        for agent in ["scanner", "trace_agent", "audit_agent", "exploit_agent", "report_agent"]:
            self.app_state.add_agent(agent)
        
        # 加载配置
        self.query_one("#interrupt_checkbox", Checkbox).value = self.app_state.audit_config.interrupt_mode
        
        # 开始审计流程
        self.app_state.is_running = True
        self.run_audit()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """复选框改变事件"""
        if event.checkbox.id == "interrupt_checkbox":
            self.interrupt_mode = event.checkbox.value
            self.app_state.audit_config.interrupt_mode = event.checkbox.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件"""
        if event.button.id == "send_button":
            self._send_user_input()
    
    def _send_user_input(self):
        """发送用户输入"""
        input_widget = self.query_one("#user_input", Input)
        user_input = input_widget.value.strip()
        
        if user_input:
            # 添加用户消息
            self.app_state.add_message("user", user_input, self.app_state.current_agent)
            
            # 清空输入
            input_widget.value = ""
            
            # 恢复输入框
            input_widget.disabled = False
            self.query_one("#send_button", Button).disabled = False
            self.is_receiving_response = False
            
            # 继续LLM对话
            self._continue_llm_conversation()
    
    def _update_agent_flow(self):
        """更新Agent流程显示"""
        agent_flow = self.query_one("#agent_flow", AgentFlow)
        current_idx = list(self.app_state.agent_statuses.keys()).index(self.app_state.current_agent) if self.app_state.current_agent else 0
        agent_flow.update_agent_status(current_idx)
    
    def _update_messages_display(self):
        """更新消息显示"""
        message_log = self.query_one("#messages_log", MessageLog)
        
        # 清空并重新添加所有消息
        message_log.clear()
        for msg in self.app_state.llm_messages:
            message_log.write(msg)
        
        # 自动滚动到底部
        message_log.scroll_end()
    
    def _continue_llm_conversation(self):
        """继续LLM对话"""
        # 这里需要集成实际的LLM调用逻辑
        # 由于篇幅限制，这里提供伪代码
        pass
    
    def run_audit(self):
        """运行审计流程"""
        # 初始化Agent流程显示，所有Agent都显示为未开始状态
        agent_flow = self.query_one("#agent_flow", AgentFlow)
        agent_flow.update_agent_status(0)
        
        # 这里需要集成实际的审计逻辑
        # 由于篇幅限制，这里提供伪代码
        pass
