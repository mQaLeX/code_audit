import os
from openai import OpenAI


class LLMClient:
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None, debug: bool = False):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.debug = debug
        self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
