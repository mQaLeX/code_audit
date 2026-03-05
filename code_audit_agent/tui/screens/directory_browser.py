"""目录浏览器"""

from textual.screen import ModalScreen
from textual.widgets import Static, Button, DirectoryTree, Label, Checkbox
from textual.containers import Container, Vertical
from textual.message import Message
import os


class DirectoryBrowser(ModalScreen):
    """目录浏览器模态窗口"""
    
    
    def compose(self) -> None:
        """组成界面"""
        yield Container(
            Vertical(
                Label("选择代码目录", id="browser_title"),
                DirectoryTree(os.getcwd(), id="dir_tree"),
                Container(
                    Button("确定", variant="primary", id="select_button"),
                    Button("取消", variant="default", id="cancel_button"),
                    id="browser_actions"
                ),
                id="browser_content"
            ),
            id="directory_browser"
        )
    
    def on_mount(self) -> None:
        """挂载时设置样式"""
        self.query_one("#browser_title").styles.text_align = "center"
        self.query_one("#browser_title").styles.text_style = "bold"
    
    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """文件选择事件"""
        # 仅处理目录选择
        if event.path and os.path.isdir(event.path):
            self._select_directory(event.path)
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件"""
        if event.button.id == "select_button":
            tree = self.query_one("#dir_tree", DirectoryTree)
            if tree.cursor_node:
                path = tree.cursor_node.data
                # 处理DirEntry对象
                if hasattr(path, 'path'):
                    path = path.path
                if path and os.path.isdir(path):
                    self._select_directory(path)
        elif event.button.id == "cancel_button":
            self.notify("已取消选择", title="提示", severity="information")
            self.dismiss()
    
    def _select_directory(self, path: str):
        """选择目录"""

        print(f"DirectoryBrowser: 消息已发送")
        self.notify(f'选择了路径{path}')
        # 不调用 dismiss，让 HomeScreen 关闭
        self.dismiss(path)
