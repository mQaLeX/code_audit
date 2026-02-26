import os
from typing import Optional
from pathlib import Path


class KnowledgeBase:
    """知识库管理器，用于加载外部输入源知识"""
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        if knowledge_base_path is None:
            knowledge_base_path = os.path.join(os.path.dirname(__file__), "..", "knowledge")
        self.knowledge_base_path = Path(knowledge_base_path)
    
    def get_full_knowledge(self, project_type: str, attack_surface: str) -> str:
        """获取完整的知识库内容"""
        knowledge_dir = self.knowledge_base_path / project_type / attack_surface
        
        input_file = knowledge_dir / "input.md"
        if input_file.exists():
            return self._load_knowledge_file(input_file)
        
        return ""
    
    def _load_knowledge_file(self, file_path: Path) -> str:
        """加载知识库文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"加载知识库文件失败: {str(e)}")
            return ""
