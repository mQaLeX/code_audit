import os
import importlib.util
import ast
from typing import List

from ..utils.models import FunctionInfo


class FunctionScanner:
    def scan_functions(self, code_dir: str, project_type: str, attack_surface: str) -> List[FunctionInfo]:
        scanner_script_path = self._get_scanner_script(project_type, attack_surface)
        
        if scanner_script_path and os.path.exists(scanner_script_path):
            return self._run_scanner_script(scanner_script_path, code_dir)
        else:
            raise Exception(f"未找到扫描脚本: {project_type} - {attack_surface}\n脚本路径: {scanner_script_path}")

    def _get_scanner_script(self, project_type: str, attack_surface: str) -> str:
        knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
        script_path = os.path.join(knowledge_dir, project_type, attack_surface, "scan.py")
        return script_path

    def _run_scanner_script(self, script_path: str, code_dir: str) -> List[FunctionInfo]:
        spec = importlib.util.spec_from_file_location("scanner", script_path)
        if spec and spec.loader:
            scanner_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(scanner_module)
            
            if hasattr(scanner_module, 'scan'):
                result = scanner_module.scan(code_dir)
                
                if result and isinstance(result, list):
                    if len(result) > 0 and isinstance(result[0], dict):
                        return [
                            FunctionInfo(
                                file_path=f['file_path'],
                                code_snippet=f['code_snippet']
                            )
                            for f in result
                        ]
                    return result
                return result
        
        raise Exception(f"扫描脚本 {script_path} 缺少 scan 函数")

