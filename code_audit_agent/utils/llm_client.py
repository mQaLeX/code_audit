import os
import json
from typing import Dict, List, Optional, Any, Callable
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text


class LLMResponse:
    """LLM 响应封装"""
    def __init__(self, content: str, finish_reason: str, usage: Dict[str, int], response_id: str, model: str):
        self.content = content
        self.finish_reason = finish_reason
        self.usage = usage
        self.response_id = response_id
        self.model = model
    
    def is_empty(self) -> bool:
        return not self.content or not self.content.strip()
    
    def get_error_message(self) -> Optional[str]:
        if not self.is_empty():
            return None
        
        error_map = {
            "content_filter": "请求被安全过滤，请修改查询内容。",
            "length": "响应被截断，请简化请求。",
            "stop": "未收到有效命令，请重新尝试。"
        }
        return error_map.get(self.finish_reason, f"未收到有效命令 (finish_reason: {self.finish_reason})")


class LLMClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = None, debug: bool = False):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.debug = debug
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self.console = Console() if debug else None

    def chat_completion(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 32768) -> str:
        try:
            if self.debug:
                self.console.print("\n")
                self.console.print(Panel.fit(
                    "[bold cyan]🤖 LLM Client Debug - Request[/bold cyan]",
                    border_style="cyan"
                ))
                
                table = Table(show_header=False, box=None, padding=(0, 1))
                table.add_column("Key", style="bold yellow")
                table.add_column("Value")
                table.add_row("Model", self.model)
                table.add_row("Temperature", str(temperature))
                table.add_row("Max Tokens", str(max_tokens))
                table.add_row("API Key", f"[dim]***{self.api_key[-4:] if self.api_key else 'None'}[/dim]")
                table.add_row("Base URL", self.base_url)
                self.console.print(table)
                
                self.console.print("\n[bold yellow]Messages:[/bold yellow]")
                for i, msg in enumerate(messages, 1):
                    role_color = {
                        "system": "bold blue",
                        "user": "bold green",
                        "assistant": "bold magenta"
                    }.get(msg["role"], "white")
                    
                    self.console.print(f"  [{role_color}]{i}. {msg['role'].upper()}:[/{role_color}]")
                    self.console.print(f"    [dim]{msg['content']}[/dim]")
                
                self.console.print("\n")
                self.console.print(Panel.fit(
                    "[bold cyan]📡 LLM Client Debug - Streaming Response[/bold cyan]",
                    border_style="cyan"
                ))
                
                try:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        stream=True
                    )
                except Exception as api_error:
                    self.console.print(f"\n[bold red]❌ LLM API调用失败:[/bold red] {str(api_error)}")
                    self.console.print(f"[bold red]❌ 请检查API密钥和base_url配置[/bold red]")
                    raise Exception(f"LLM API调用失败: {str(api_error)}")
                
                full_content = ""
                chunk_count = 0
                for chunk in response:
                    chunk_count += 1
                    if chunk.choices and len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        full_content += content
                        self.console.print(content, end="")
                self.console.print()
                
                if chunk_count == 0:
                    self.console.print("\n[bold yellow]⚠️  未收到任何响应块[/bold yellow]")
                
                if not full_content or not full_content.strip():
                    self.console.print("\n[bold red]❌ LLM返回了空内容[/bold red]")
                    raise Exception("LLM返回了空内容，可能被安全过滤或API调用失败")
                
                self.console.print("\n")
                self.console.print(Panel.fit(
                    "[bold cyan]📊 LLM Client Debug - Response Summary[/bold cyan]",
                    border_style="cyan"
                ))
                
                summary_table = Table(show_header=False, box=None, padding=(0, 1))
                summary_table.add_column("Key", style="bold yellow")
                summary_table.add_column("Value")
                summary_table.add_row("Total chunks", str(chunk_count))
                summary_table.add_row("Content length", f"{len(full_content)} characters")
                self.console.print(summary_table)
                self.console.print()
                
                return full_content
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            if "LLM API调用失败" in str(e):
                raise
            raise Exception(f"LLM API调用失败: {str(e)} api_key: {self.api_key} base_url: {self.base_url} model: {self.model}")

    def chat_completion_with_metadata(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> LLMResponse:
        """调用 LLM 并返回完整响应元数据"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            
            choice = response.choices[0]
            content = choice.message.content or ""
            
            return LLMResponse(
                content=content,
                finish_reason=choice.finish_reason,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                },
                response_id=response.id,
                model=response.model
            )
        except Exception as e:
            raise Exception(f"LLM API调用失败: {str(e)}")

    def generate_with_system_prompt(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.chat_completion(messages, temperature=temperature)

    def generate_json_response(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        response_text = self.chat_completion(messages, temperature=0.3)
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            return {"raw_response": response_text}

    def chat_completion_structured(self, messages: List[Dict[str, str]], response_schema: Dict[str, Any], temperature: float = 0.7, max_tokens: int = 32768) -> Any:
        """使用 OpenAI 结构化输出功能
        
        Args:
            messages: 消息列表
            response_schema: 响应的 JSON schema
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            结构化的响应对象
        """
        try:
            # 当模型是glm时，使用json_object
            if 'glm' in self.model:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={
                        "type": "json_object"
                    }
                )
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "trace_result",
                            "strict": True,
                            "schema": response_schema
                        }
                    }
                )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            #打印详细和openai返回的错误信息
            self.console.print(f"[bold red]LLM 结构化输出调用失败: {str(e)}[/bold red]")
            self.console.print(f"[bold red]OpenAI 返回的错误信息: {response.choices[0].message.content}[/bold red]")
            raise Exception(f"LLM 结构化输出调用失败: {str(e)}")

    