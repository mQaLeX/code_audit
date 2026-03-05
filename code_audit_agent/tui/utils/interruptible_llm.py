"""LLM客户端包装器，支持干扰模式"""

from typing import List, Dict, Any, Optional
from code_audit_agent.utils import LLMClient
from code_audit_agent.tui.state import AppState


class InterruptibleLLMClient:
    """可中断的LLM客户端，支持干扰模式"""
    
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.llm_client = LLMClient(
            api_key=app_state.config.api_key,
            base_url=app_state.config.base_url,
            model=app_state.config.model,
            debug=app_state.config.debug
        )
    
    def chat_with_interrupt(
        self,
        messages: List[Dict[str, str]],
        interrupt_mode: bool = False,
        **kwargs
    ) -> Optional[str]:
        """
        带中断功能的聊天方法
        
        Args:
            messages: 消息列表
            interrupt_mode: 是否启用干扰模式
            **kwargs: 其他参数
            
        Returns:
            LLM响应内容
        """
        # 如果启用干扰模式，检查是否需要等待用户输入
        if interrupt_mode and self.app_state.is_paused:
            # 等待用户输入
            self.app_state.is_paused = False
            # 这里需要实现等待用户输入的逻辑
            # 由于Textual的异步特性，这里提供伪代码
            pass
        
        # 调用LLM
        response = self.llm_client.chat(messages=messages, **kwargs)
        
        # 如果正在接收响应，暂停
        if self.app_state.is_receiving_response:
            self.app_state.is_paused = True
        
        return response
    
    def stream_chat_with_interrupt(
        self,
        messages: List[Dict[str, str]],
        interrupt_mode: bool = False,
        **kwargs
    ):
        """
        流式聊天方法，支持干扰模式
        
        Args:
            messages: 消息列表
            interrupt_mode: 是否启用干扰模式
            **kwargs: 其他参数
            
        Yields:
            流式响应内容
        """
        # 如果启用干扰模式，检查是否需要等待用户输入
        if interrupt_mode and self.app_state.is_paused:
            # 等待用户输入
            self.app_state.is_paused = False
            # 这里需要实现等待用户输入的逻辑
            pass
        
        # 调用LLM流式接口
        response = self.llm_client.chat(messages=messages, stream=True, **kwargs)
        
        # 流式返回
        for chunk in response:
            # 检查是否需要暂停
            if self.app_state.is_paused:
                break
            
            yield chunk
        
        # 标记正在接收响应
        self.app_state.is_receiving_response = True
