"""LLM消息组件"""

from textual.reactive import Reactive
from textual.widgets import Static, Collapsible
from typing import Optional


class LLMMessage(Static):
    """LLM消息组件"""
    
    collapsed: Reactive[bool] = Reactive(True)
    
    def __init__(self, role: str, content: str, id: Optional[str] = None):
        super().__init__(id=id)
        self.role = role
        self.content = content
        self.title = self._generate_title()
    
    def _generate_title(self) -> str:
        """生成标题"""
        if self.role == "user":
            return "👤 用户消息"
        elif self.role == "assistant":
            # 检查是否包含工具调用
            if "tool" in self.content.lower() or "submit" in self.content.lower():
                return "🤖 工具调用"
            return "🤖 AI响应"
        else:
            return f"📝 {self.role}消息"
    
    def compose(self):
        """组成界面"""
        with Collapsible(title=self.title, collapsed=self.collapsed):
            yield Static(self.content, id="message_content")
    
    def toggle_collapsed(self):
        """切换折叠状态"""
        self.collapsed = not self.collapsed
    
    def on_mount(self) -> None:
        """挂载时设置样式"""
        self.add_class("llm-message")
        if self.role == "user":
            self.add_class("user-message")
        else:
            self.add_class("assistant-message")
