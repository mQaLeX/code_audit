"""Agent流程可视化组件"""

from textual.widgets import Static
from textual.containers import Container, Horizontal
from typing import List


class AgentFlow(Static):
    """Agent流程可视化组件"""
    
    def __init__(self, agents: List[str], id: str):
        super().__init__(id=id)
        self.agents = agents
        self.current_agent = 0
        self.id_container = id
    def _gen_str(self) -> str:
        """生成整个Agent字符串"""
        ret = ''
        for i in range(len(self.agents)):
            if i == self.current_agent:
                ret += f"[red]{self.agents[i]}[/]->"
            else:
                ret += f"[dim]{self.agents[i]}[/]->"
        return ret
    
    def compose(self):
        """组成界面"""
        # 初始化内容
        self.update(self._gen_str())
        # 返回空迭代器
        yield from ()
        
    
    def update_agent_status(self, current_idx: int):
        """更新Agent状态"""
        self.current_agent = current_idx
        self.update(self._gen_str())