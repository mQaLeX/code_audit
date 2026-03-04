import json
import re
from typing import Dict, Any, List


def clean_and_parse(response: str) -> Dict[str, Any]:
    """
    清洗 LLM 响应并解析 JSON
    
    Args:
        response: LLM 的原始响应文本
        
    Returns:
        解析后的字典
        
    Raises:
        json.JSONDecodeError: 解析失败时抛出
    """
    if not response:
        raise json.JSONDecodeError("空响应", response, 0)
    
    text = response.strip()
    
    text = re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<reasoning[\s\S]*?</reasoning\s*>', '', text, flags=re.IGNORECASE)
    
    text = text.strip()
    
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if code_block:
        text = code_block.group(1).strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    json_match = re.search(r'\{[\s\S]*\}', text)
    if json_match:
        return json.loads(json_match.group())
    
    raise json.JSONDecodeError("无法提取有效JSON", text, 0)


def clean_and_parse_list(response: str) -> List[Dict[str, Any]]:
    """
    清洗 LLM 响应并解析 JSON 数组
    
    Args:
        response: LLM 的原始响应文本
        
    Returns:
        解析后的列表
        
    Raises:
        json.JSONDecodeError: 解析失败时抛出
    """
    if not response:
        raise json.JSONDecodeError("空响应", response, 0)
    
    text = response.strip()
    
    text = re.sub(r'<think[\s\S]*?</think\s*>', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<reasoning[\s\S]*?</reasoning\s*>', '', text, flags=re.IGNORECASE)
    
    text = text.strip()
    
    code_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if code_block:
        text = code_block.group(1).strip()
    
    try:
        result = json.loads(text)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass
    
    json_match = re.search(r'\[[\s\S]*\]', text)
    if json_match:
        return json.loads(json_match.group())
    
    raise json.JSONDecodeError("无法提取有效JSON数组", text, 0)
