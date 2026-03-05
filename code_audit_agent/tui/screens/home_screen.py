"""主界面"""

from textual.screen import Screen
from textual.widgets import (
    Static,
    Button,
    Input,
    Tree,
    Checkbox,
    ContentSwitcher,
    Label,
    RichLog,
    Header,
    Footer,
)
from textual.containers import Container, Vertical, Horizontal
from typing import List, Tuple
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from code_audit_agent.utils.config import get_config
from .directory_browser import DirectoryBrowser
from .audit_screen import AuditScreen


class DirectoryInput(Container):
    """目录输入组件"""
    
    def __init__(self):
        super().__init__(id="directory_input")
        self.input = Input(
            placeholder="输入代码目录路径，或点击浏览按钮选择",
            id="code_dir_input"
        )
        self.browse_button = Button("浏览", id="browse_button")
    
    def compose(self):
        yield self.input
        yield self.browse_button
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """点击浏览按钮"""
        if event.button.id == "browse_button":
            from ..app import CodeAuditApp
            if isinstance(self.app, CodeAuditApp):
                self.app.push_screen(DirectoryBrowser(), self.handle_directory_selection)

    def handle_directory_selection(self, path: str) -> None:
        """处理目录选择"""
        self.input.value = str(path)

class KnowledgeTree(Container):
    """知识库树形选择组件"""
    
    def __init__(self):
        super().__init__()
        self.knowledge_dir = self._get_knowledge_base_dir()
        self._tree_widget = None
    
    def _get_knowledge_base_dir(self) -> str:
        """获取知识库目录"""
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        return os.path.join(base_dir, 'knowledge')
    
    def compose(self):
        with Vertical():
            yield Static("选择项目类型和攻击面:", id="tree_label")
            self._tree_widget = Tree(label="知识库", id="knowledge_tree")
            self._tree_widget.guide_depth = 3
            self._tree_widget.show_guides = True
            self._tree_widget.show_root = False
            yield self._tree_widget
            yield Static("提示：点击节点进行选择", id="tree_hint")
    
    def on_mount(self) -> None:
        """挂载时构建树"""
        self._build_tree()
    
    def _build_tree(self):
        """构建知识库树"""
        if not os.path.exists(self.knowledge_dir):
            self._tree_widget.root.remove_children()
            self._tree_widget.add_leaf("知识库目录不存在")
            return
        
        # 清空现有树
        self._tree_widget.root.remove_children()
        
        # 遍历知识库目录
        for project_type in sorted(os.listdir(self.knowledge_dir)):
            project_path = os.path.join(self.knowledge_dir, project_type)
            if not os.path.isdir(project_path):
                continue
            
            # 创建项目类型节点
            project_node = self._tree_widget.root.add(
                f"📁 {project_type}",
                data={"type": "project", "name": project_type, "path": project_path}
            )
            project_node.expand()
            
            # 遍历攻击面
            for attack_surface in sorted(os.listdir(project_path)):
                attack_path = os.path.join(project_path, attack_surface)
                if not os.path.isdir(attack_path):
                    continue
                
                # 创建攻击面节点
                attack_node = project_node.add(
                    f"📁 {attack_surface}",
                    data={"type": "attack_surface", "name": attack_surface, "path": attack_path}
                )
                attack_node.expand()


class HomeScreen(Screen):
    """主界面"""
    
    def compose(self) -> None:
        """组成界面"""
        yield Header()
        
        with Vertical(id="main_content"):
            yield Static("代码审计AI Agent - TUI", id="title")
            yield DirectoryInput()
            yield KnowledgeTree()
            
            with Horizontal(id="action_buttons"):
                yield Button("确定", variant="primary", id="start_button")
                yield Button("重置", variant="default", id="reset_button")
        
        yield Footer()
    
    def on_mount(self) -> None:
        """挂载时设置样式"""
        self.query_one("#title").styles.text_align = "center"
        self.query_one("#title").styles.text_style = "bold"
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """按钮按下事件"""
        if event.button.id == "start_button":
            self._start_audit()
        elif event.button.id == "reset_button":
            self._reset()
    
    def _start_audit(self):
        """开始审计"""
        # 获取代码目录
        code_dir_input = self.query_one("#code_dir_input", Input)
        code_dir = code_dir_input.value.strip()
        
        if not code_dir:
            self.notify("请输入代码目录路径", severity="error")
            return
        
        if not os.path.exists(code_dir):
            self.notify("代码目录不存在", severity="error")
            return
        
        # 获取树形组件选中项
        knowledge_tree = self.query_one("#knowledge_tree", Tree)
        cursor_node = knowledge_tree.cursor_node
        
        if not cursor_node:
            self.notify("请在树形组件中选择一个项目类型或攻击面", severity="error")
            return
        
        # 解析 project_type 和 attack_surface
        project_type = None
        attack_surface = None
        
        node = cursor_node
        while node:
            data = node.data
            if data:
                if data.get("type") == "attack_surface":
                    attack_surface = data.get("name")
                    if not project_type and node.parent and node.parent.data:
                        project_type = node.parent.data.get("name")
                        break
                elif data.get("type") == "project":
                    project_type = data.get("name")
                    break
            node = node.parent
        
        if not project_type:
            self.notify("请选择一个项目类型", severity="error")
            return
        
        if not attack_surface:
            self.notify("请选择一个攻击面", severity="error")
            return
        
        # 保存配置
        from code_audit_agent.tui.state import AppState
        app_state = AppState()
        app_state.audit_config.code_dir = code_dir
        app_state.audit_config.project_types = [project_type]
        app_state.audit_config.attack_surfaces = [attack_surface]
        
        # 切换到审计界面
        self.app.push_screen(AuditScreen())
    
    def _reset(self):
        """重置界面"""
        # 清空输入
        self.query_one("#code_dir_input", Input).value = ""
        
        # 取消所有复选框
        for checkbox in self.query(Checkbox):
            checkbox.value = False
        
        self.notify("已重置", severity="information")
