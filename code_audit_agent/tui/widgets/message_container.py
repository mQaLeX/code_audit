"""LLM消息容器"""

from textual.widgets import Static, RichLog
from textual.containers import Container, Vertical
from typing import List, Optional
from ..widgets.llm_message import LLMMessage


class MessageLog(RichLog):
    """消息日志组件，支持流式显示"""
    
    def __init__(self, id: str = "message_log"):
        super().__init__(id=id)
        self.write_only = True
        self.auto_scroll = True
    
    def add_message(self, role: str, content: str) -> LLMMessage:
        """添加消息"""
        msg = LLMMessage(role=role, content=content)
        self.write(msg)
        return msg
    
    def update_message(self, msg: LLMMessage, new_content: str):
        """更新消息内容（流式更新）"""
        # 这里需要实现流式更新逻辑
        pass


class MessageContainer(Container):
    """消息容器组件"""
    
    def __init__(self, id: str = "message_container"):
        super().__init__(id=id)
        self.messages: List[LLMMessage] = []
        self.current_message: Optional[LLMMessage] = None
    
    def compose(self):
        """组成界面"""
        yield Static("LLM对话历史", id="messages_title")
        yield MessageLog(id="messages_log")
    
    def add_user_message(self, content: str):
        """添加用户消息"""
        msg = LLMMessage(role="user", content=content)
        self.messages.append(msg)
        self.query_one("#messages_log", MessageLog).write(msg)
        self.current_message = None
    
    def add_assistant_message_start(self) -> LLMMessage:
        """开始添加AI消息（返回消息对象用于流式更新）"""
        msg = LLMMessage(role="assistant", content="")
        self.messages.append(msg)
        self.current_message = msg
        # 先添加一个折叠的容器
        self.query_one("#messages_log", MessageLog).write(msg)
        return msg
    
    def update_assistant_message(self, content: str):
        """更新AI消息内容（流式）"""
        if self.current_message:
            self.current_message.content += content
            # 更新显示
            self.query_one("#messages_log", MessageLog).write(content, end="")
    
    def complete_assistant_message(self):
        """完成AI消息，自动折叠"""
        if self.current_message:
            self.current_message.collapsed = True
            self.current_message = None
