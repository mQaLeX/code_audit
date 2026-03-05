"""TUI状态管理"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from code_audit_agent.tui.widgets.llm_message import LLMMessage


@dataclass
class AuditConfig:
    """审计配置"""
    code_dir: str = ""
    project_types: List[str] = field(default_factory=list)
    attack_surfaces: List[str] = field(default_factory=list)
    interrupt_mode: bool = False


@dataclass
class AgentStatus:
    """Agent状态"""
    name: str
    current: bool = False
    completed: bool = False
    messages: List[LLMMessage] = field(default_factory=list)
    current_message: Optional[LLMMessage] = None


class AppState:
    """全局状态管理"""
    _instance: Optional['AppState'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self.audit_config = AuditConfig()
        self.agent_statuses: Dict[str, AgentStatus] = {}
        self.llm_messages: List[LLMMessage] = []
        self.current_agent: Optional[str] = None
        self.is_running: bool = False
        self.is_paused: bool = False
        self.audit_results: List[Dict[str, Any]] = []
    
    def add_agent(self, name: str):
        """添加Agent"""
        self.agent_statuses[name] = AgentStatus(name=name)
    
    def set_current_agent(self, name: str):
        """设置当前Agent"""
        if self.current_agent and self.current_agent in self.agent_statuses:
            self.agent_statuses[self.current_agent].current = False
            if self.agent_statuses[self.current_agent].current_message:
                self.agent_statuses[self.current_agent].current_message.collapsed = True
        
        self.current_agent = name
        if name in self.agent_statuses:
            self.agent_statuses[name].current = True
    
    def add_message(self, role: str, content: str, agent_name: str = None):
        """添加LLM消息"""
        msg = LLMMessage(role=role, content=content)
        self.llm_messages.append(msg)
        
        if agent_name and agent_name in self.agent_statuses:
            self.agent_statuses[agent_name].messages.append(msg)
            self.agent_statuses[agent_name].current_message = msg
        
        return msg
    
    def complete_agent(self, name: str):
        """标记Agent完成"""
        if name in self.agent_statuses:
            self.agent_statuses[name].completed = True
            self.agent_statuses[name].current = False
            if self.agent_statuses[name].current_message:
                self.agent_statuses[name].current_message.collapsed = True
    
    def reset(self):
        """重置状态"""
        self.audit_config = AuditConfig()
        self.agent_statuses = {}
        self.llm_messages = []
        self.current_agent = None
        self.is_running = False
        self.is_paused = False
        self.audit_results = []
