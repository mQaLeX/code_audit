import os
import re
from typing import Dict, Any, Optional
from .lsp_client import LSPClient





class CodeEnvironment:
    """代码环境，用于执行 ACI 命令"""
    
    def __init__(self, code_dir: Optional[str] = None):
        self.code_dir = code_dir
        self.current_file = None
        self.current_lines = []
        self.current_start = 1
        self.current_end = 100
        self.lsp_client = None
        self._lsp_available = False
        
        if code_dir:
            try:
                self.lsp_client = LSPClient(workspace_root=code_dir)
                if self.lsp_client.start() and self.lsp_client.initialize():
                    self._lsp_available = True
            except Exception:
                self._lsp_available = False
                print("LSP 初始化失败", file=sys.stderr)
    
    def is_lsp_available(self) -> bool:
        """检查 LSP 是否可用"""
        return self._lsp_available
    
    def get_tools_prompt(self) -> str:
        """获取 ACI 工具提示词"""
        prompt = """## ACI 工具

### 文件操作
- `open <file>[:start-end]` - 查看文件内容，默认显示100行
  例：open main.c:1-50

- `view` - 重新查看当前打开的文件

### 代码搜索
- `search <query>` - 在代码库中搜索
  例：search validate_hostname

- `search_file <query>` - 在当前文件中搜索
  例：search_file TODO"""
        
        if self._lsp_available:
            prompt += """

### LSP 工具（优先使用lsp工具）
- `go_to_def <file>:<line>:<symbol>` - 查看指定符号的定义
  例：
  有以下代码
  main.c
  ```c
  1|int web_handler(const ctx *ctx) {
  2|  char *hostname = get_param(ctx, "hostname");
  3|  if (!validate_hostname(hostname)) {
  4|    return 400;
  5|  }
  6|  return 200;
  7| }
  ```
  外部输入为 ctx，ctx 中包含 hostname 参数，要继续追踪 validate_hostname 函数的定义来分析hostname外部输入怎么影响程序行为，就有一下命令：
  ```
  go_to_def main.c:2:validate_hostname
  ```

- `find_refs <file>:<line>:<symbol>` - 查找符号的所有引用
  例：
  有以下代码
  main.c
  ```c
  1|int web_handler(char *input_param) {
  2|  popen(input_param, "r");
  6|  return 200;
  7| }
  ```
  此时 input_param 是外部输入，要查找 input_param 被使用的地方，就有一下命令：
  ```
  find_refs main.c:1:web_handler
  ```
"""
        
        prompt += """

### 任务完成
- `submit` - 提交追踪结果并结束任务"""
        
        return prompt
    
    
    def execute(self, action: str) -> Dict[str, Any]:
        """执行 ACI 命令并返回结果"""
        action = action.strip()
        
        if action.startswith("open "):
            return self._cmd_open(action[5:].strip())
        elif action.startswith("go_to_def "):
            return self._cmd_goto(action[10:].strip())
        elif action.startswith("find_refs "):
            return self._cmd_find_refs(action[10:].strip())
        elif action.startswith("search "):
            return self._cmd_search(action[7:].strip())
        elif action.startswith("search_file "):
            return self._cmd_search_file(action[11:].strip())
        elif action == "view":
            return self._cmd_view()
        elif action == "submit":
            return {"done": True, "output": "任务完成"}
        else:
            return {"error": f"未知命令: {action}", "done": False}
    
    def _cmd_open(self, args: str) -> Dict[str, Any]:
        """打开文件并显示内容 输入为"""
        try:
            parts = args.split(":")
            file_path = parts[0].strip()
            
            if len(parts) > 1:
                line_range = parts[1].strip()
                if "-" in line_range:
                    start_end = line_range.split("-")
                    self.current_start = int(start_end[0])
                    self.current_end = int(start_end[1])
                else:
                    self.current_start = int(line_range)
                    self.current_end = self.current_start + 100
            else:
                self.current_start = 1
                self.current_end = 100
            
            if self.code_dir and not os.path.isabs(file_path):
                file_path = os.path.join(self.code_dir, file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                self.current_lines = f.readlines()
            
            self.current_file = file_path
            
            total_lines = len(self.current_lines)
            display_end = min(self.current_end, total_lines)
            
            output = f"文件: {file_path}\n"
            output += f"总行数: {total_lines}\n"
            output += f"显示行: {self.current_start}-{display_end}\n\n"
            for i, line in enumerate(self.current_lines[self.current_start-1:display_end], start=self.current_start):
                output += f"{i:6d} | {line}"
            
            return {"done": False, "output": output}
        except Exception as e:
            return {"error": f"打开文件失败: {str(e)}", "done": False}
    
    def _cmd_view(self) -> Dict[str, Any]:
        """重新查看当前文件"""
        if not self.current_file:
            return {"error": "没有打开的文件", "done": False}
        
        display_end = min(self.current_end, len(self.current_lines))
        output = f"文件: {self.current_file}\n"
        output += f"显示行: {self.current_start}-{display_end}\n\n"
        for i, line in enumerate(self.current_lines[self.current_start-1:display_end], start=self.current_start):
            output += f"{i:6d} | {line}"
        
        return {"done": False, "output": output}
    
    def _cmd_goto(self, args: str) -> Dict[str, Any]:
        """跳转到指定位置查看定义 输入为 main.c:2:validate_hostname"""
        if not self.lsp_client:
            return {"error": "LSP未启用", "done": False}
        
        try:
            parts = args.split(":")
            if len(parts) != 3:
                return {"error": "格式错误，应为: file:line:symbol", "done": False}
            
            file_path = parts[0].strip()
            # 检查文件是否存在
            file_full_path = os.path.join(self.code_dir, file_path) if self.code_dir else file_path
            if not os.path.exists(file_full_path):
                return {"error": f"文件不存在: {file_full_path}", "done": False}
            file_full_path = os.path.abspath(file_full_path)
            line = int(parts[1].strip())
            symbol = parts[2].strip()
            character = -1
            #打开对应文件和行号，看符号具体是在多少列
            with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                print(f"文件总共有{len(lines)}行")
                if line > len(lines):
                    return {"error": "行号超出文件范围", "done": False}
                line_content = lines[line-1]
                character = line_content.find(symbol)
                print(f"{line_content}")
                if character == -1:
                    return {"error": "符号未找到:"+line_content, "done": False}

            
            self.lsp_client.open_document(file_full_path)
            definitions = self.lsp_client.get_definition(file_full_path, line, character+1)
            
            if not definitions:
                return {"error": "未找到定义", "done": False}
            
            def_info = definitions[0]
            def_file_path = def_info.get("uri", file_path)
            if def_file_path.startswith("file://"):
                def_file_path = def_file_path[7:]
            
            range_info = def_info.get("range", {})
            start_line = range_info.get("start", {}).get("line", 0) + 1
            end_line = range_info.get("end", {}).get("line", 0) + 1
            
            # code_snippet 加上行号
            with open(def_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                # 查找函数体的结束位置
                # 从函数定义行开始，找到匹配的右大括号
                brace_count = 0
                found_start_brace = False
                actual_end_line = end_line
                
                for i in range(start_line - 1, len(lines)):
                    line_content = lines[i]
                    for char in line_content:
                        if char == '{':
                            brace_count += 1
                            found_start_brace = True
                        elif char == '}':
                            brace_count -= 1
                            if found_start_brace and brace_count == 0:
                                actual_end_line = i + 1
                                break
                    if found_start_brace and brace_count == 0:
                        break
                
                code_snippet = ''.join(f"{i+start_line-1:6d} | {line}" for i, line in enumerate(lines[start_line-1:actual_end_line]))
            
            output = f"定义位置: {def_file_path}:{start_line}-{actual_end_line}\n\n"
            output += code_snippet
            
            return {"done": False, "output": output}
        except Exception as e:
            return {"error": f"跳转失败: {str(e)}", "done": False}
    
    def _cmd_find_refs(self, args: str) -> Dict[str, Any]:
        """查找符号的所有引用"""
        if not self.lsp_client:
            return {"error": "LSP未启用", "done": False}
        
        try:
            parts = args.split(":")
            if len(parts) != 3:
                return {"error": "格式错误，应为: file:line:col", "done": False}
            
            file_path = parts[0].strip()
            line = int(parts[1].strip())
            character = int(parts[2].strip())
            
            if self.code_dir and not os.path.isabs(file_path):
                file_path = os.path.join(self.code_dir, file_path)
            file_full_path = os.path.abspath(file_path)
            
            self.lsp_client.open_document(file_full_path)
            references = self.lsp_client.get_references(file_full_path, line, character)
            
            if not references:
                return {"error": "未找到引用", "done": False}
            
            output = f"找到 {len(references)} 个引用:\n\n"
            for i, ref_info in enumerate(references[:10], 1):
                ref_file_path = ref_info.get("uri", file_path)
                if ref_file_path.startswith("file://"):
                    ref_file_path = ref_file_path[7:]
                
                range_info = ref_info.get("range", {})
                start_line = range_info.get("start", {}).get("line", 0) + 1
                end_line = range_info.get("end", {}).get("line", 0) + 1
                
                output += f"{i}. {ref_file_path}:{start_line}-{end_line}\n"
            
            return {"done": False, "output": output}
        except Exception as e:
            return {"error": f"查找引用失败: {str(e)}", "done": False}
    
    def _cmd_search(self, query: str) -> Dict[str, Any]:
        """在代码库中搜索"""
        if not self.code_dir:
            return {"error": "代码目录未设置", "done": False}
        
        try:
            from pathlib import Path
            
            results = []
            max_results = 10
            
            for file_path in Path(self.code_dir).rglob("*.c"):
                if len(results) >= max_results:
                    break
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for i, line in enumerate(lines, 1):
                        if re.search(query, line, re.IGNORECASE):
                            start_line = max(1, i - 3)
                            end_line = min(len(lines), i + 3)
                            code_snippet = ''.join(lines[start_line-1:end_line])
                            
                            results.append({
                                "file_path": str(file_path),
                                "line_start": start_line,
                                "line_end": end_line,
                                "code_snippet": code_snippet,
                                "match_line": i,
                                "match_content": line.strip()
                            })
                            
                            if len(results) >= max_results:
                                break
                except Exception:
                    continue
            
            output = f"搜索 '{query}' 找到 {len(results)} 个结果:\n\n"
            for i, result in enumerate(results, 1):
                output += f"{i}. {result['file_path']}:{result['match_line']}\n"
                output += f"   {result['match_content']}\n\n"
            
            return {"done": False, "output": output}
        except Exception as e:
            return {"error": f"搜索失败: {str(e)}", "done": False}
    
    def _cmd_search_file(self, query: str) -> Dict[str, Any]:
        """在当前文件中搜索"""
        if not self.current_file:
            return {"error": "没有打开的文件", "done": False}
        
        try:
            results = []
            
            for i, line in enumerate(self.current_lines, 1):
                if re.search(query, line, re.IGNORECASE):
                    start_line = max(1, i - 3)
                    end_line = min(len(self.current_lines), i + 3)
                    code_snippet = ''.join(self.current_lines[start_line-1:end_line])
                    
                    results.append({
                        "line_start": start_line,
                        "line_end": end_line,
                        "code_snippet": code_snippet,
                        "match_line": i,
                        "match_content": line.strip()
                    })
            
            output = f"在当前文件中搜索 '{query}' 找到 {len(results)} 个结果:\n\n"
            for i, result in enumerate(results, 1):
                output += f"{i}. 行 {result['match_line']}\n"
                output += f"   {result['match_content']}\n\n"
            
            return {"done": False, "output": output}
        except Exception as e:
            return {"error": f"搜索文件失败: {str(e)}", "done": False}
