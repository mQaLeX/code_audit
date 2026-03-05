"""TUI工具模块"""

from typing import Optional
import os
import sys

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from code_audit_agent.utils import LLMClient
from code_audit_agent.utils.config import get_config


class AsyncWorker:
    """异步工作器，用于处理耗时操作"""
    
    def __init__(self):
        self.config = get_config()
    
    def create_llm_client(self) -> LLMClient:
        """创建LLM客户端"""
        return LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
            debug=self.config.debug
        )


class TerminalCompat:
    """终端兼容性检测"""
    
    @staticmethod
    def supports_mouse() -> bool:
        """检测是否支持鼠标"""
        # 检查TERM环境变量
        term = os.environ.get("TERM", "")
        if "xterm" in term or "rxvt" in term or "screen" in term:
            return True
        return False
    
    @staticmethod
    def get_terminal_size() -> tuple:
        """获取终端大小"""
        import shutil
        size = shutil.get_terminal_size()
        return (size.columns, size.lines)
