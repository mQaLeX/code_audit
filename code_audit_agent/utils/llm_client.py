import os
import signal
import time
from typing import Optional
from openai import OpenAI, RateLimitError
from .config import get_config
config = get_config()

_interrupted = False
_current_response = None

def _signal_handler(signum, frame):
    global _interrupted, _current_response
    _interrupted = True
    print("\n\n收到中断信号，正在取消请求...")
    if _current_response is not None:
        try:
            _current_response.close()
        except Exception:
            pass
    raise KeyboardInterrupt("用户中断")

signal.signal(signal.SIGINT, _signal_handler)


class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, debug: bool = False):
        self.api_key = api_key or config.api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or config.base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
        self.model = model or config.model or os.getenv("OPENAI_MODEL") or "gpt-4o"
        self.debug = debug
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        self._cancelled = False
        print(f"初始化 LLMClient: 模型={self.model}, 调试={self.debug}, 基础URL={self.base_url}")
    
    def cancel(self):
        self._cancelled = True
    
    @staticmethod
    def is_interrupted():
        return _interrupted


    def chat(self, think: bool = True, max_retries: int = 3, **kwargs):
        global _interrupted, _current_response
        _interrupted = False
        self._cancelled = False
        _current_response = None
        
        last_error = None
        for attempt in range(max_retries):
            if _interrupted or self._cancelled:
                print("请求已取消")
                return None
            
            try:
                extra_body = {}
                if think:
                    extra_body["thinking"] = {
                        "type": "enabled",
                    }
                else:
                    print("思考功能已禁用")
                    extra_body["thinking"] = {
                        "type": "disabled",
                    }
                response = self.client.chat.completions.create(
                    model=self.model,
                    stream=True,
                    extra_body=extra_body,
                    **kwargs
                )
                _current_response = response
                
                if config.debug:
                    full_content = ""
                    try:
                        if self.debug:
                            first_reasoning = True
                            first_content = True
                            for chunk in response:
                                if _interrupted or self._cancelled:
                                    print("\n请求已取消")
                                    return None
                                
                                delta = chunk.choices[0].delta
                                
                                reasoning_content = getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                                if reasoning_content:
                                    prefix = "\n🤔 " if first_reasoning else ""
                                    print(f"{prefix}{reasoning_content}", end="", flush=True)
                                    first_reasoning = False
                                
                                content = getattr(delta, 'content', None)
                                if content:
                                    full_content += content
                                    prefix = "\n📝 " if first_content else ""
                                    print(f"{prefix}{content}", end="", flush=True)
                                    first_content = False
                            print()
                        else:
                            for chunk in response:
                                if _interrupted or self._cancelled:
                                    print("\n请求已取消")
                                    return None
                                
                                delta = chunk.choices[0].delta
                                content = getattr(delta, 'content', None)
                                if content:
                                    full_content += content
                    finally:
                        _current_response = None
                    
                    return full_content
                    
            except KeyboardInterrupt:
                print("\n请求已取消")
                return None
            except RateLimitError as e:
                last_error = e
                wait_time = (attempt + 1) * 5
                print(f"速率限制，等待 {wait_time} 秒后重试 ({attempt + 1}/{max_retries})...")
                time.sleep(wait_time)
            except Exception as e:
                print(f"Error in chat completion: {e}")
                return None
            finally:
                _current_response = None
        
        print(f"达到最大重试次数，请求失败: {last_error}")
        return None
