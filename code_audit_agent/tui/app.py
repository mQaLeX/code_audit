"""TUI主应用"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Button, Label, Static
from textual.screen import Screen
from textual import events
from typing import Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from .screens.home_screen import HomeScreen
from .screens.audit_screen import AuditScreen
from .screens.directory_browser import DirectoryBrowser


class CodeAuditApp(App):
    """代码审计TUI应用"""
    
    CSS_PATH = None
    TITLE = "代码审计AI Agent"
    SUB_TITLE = "TUI Version"
    
    def on_mount(self) -> None:
        """挂载时显示主界面"""
        self.push_screen(HomeScreen())
    
    def action_open_directory_browser(self) -> None:
        """打开目录浏览器"""
        self.push_screen(DirectoryBrowser())
    
    def action_start_audit(self) -> None:
        """开始审计"""
        self.push_screen(AuditScreen())


def main():
    """启动应用"""
    app = CodeAuditApp()
    app.run()


if __name__ == "__main__":
    main()
