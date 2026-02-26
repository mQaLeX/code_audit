import os
import json
import sys
from pathlib import Path
from typing import List

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

from utils.lsp_client import LSPClient
from utils.models import FunctionInfo

try:
    from ast_grep_py import SgRoot
except ImportError:
    print("ast-grep-py未安装，使用备用方法", file=sys.stderr)
    SgRoot = None


def scan(code_dir: str) -> List[FunctionInfo]:
    """
    扫描代码目录，查找mg_set_request_handler调用并提取回调函数信息
    """
    functions = []
    
    code_dir = os.path.abspath(code_dir)
    
    c_files = []
    for root, _, files in os.walk(code_dir):
        for file in files:
            if file.endswith('.c') or file.endswith('.cpp'):
                file_path = os.path.join(root, file)
                if '_deps' not in file_path:
                    c_files.append(file_path)
    
    if not c_files:
        print(f"未找到C/C++文件在目录: {code_dir}", file=sys.stderr)
        return functions
    
    print(f"找到 {len(c_files)} 个C/C++文件", file=sys.stderr)
    
    if not SgRoot:
        print("ast-grep-py未安装", file=sys.stderr)
        return functions
    
    lsp_client = None
    try:
        lsp_client = LSPClient(workspace_root=code_dir)
        if lsp_client.start():
            lsp_client.initialize()
            print("LSP客户端初始化成功", file=sys.stderr)
        else:
            print("LSP客户端启动失败", file=sys.stderr)
            lsp_client = None
    except Exception as e:
        print(f"LSP客户端初始化失败: {str(e)}", file=sys.stderr)
        lsp_client = None
    
    try:
        for c_file in c_files:
            file_functions = _scan_file_with_ast_grep(c_file, code_dir, lsp_client)
            functions.extend(file_functions)
    finally:
        if lsp_client:
            lsp_client.stop()
    
    print(f"共发现 {len(functions)} 个回调函数", file=sys.stderr)
    return functions


def _scan_file_with_ast_grep(file_path: str, code_dir: str, lsp_client: LSPClient = None) -> list:
    """
    使用ast-grep-py扫描单个文件，查找mg_set_request_handler调用
    """
    functions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            code = f.read()
    except Exception as e:
        print(f"读取文件失败 {file_path}: {str(e)}", file=sys.stderr)
        return functions
    
    try:
        root = SgRoot(code, "c")
        node = root.root()
    except Exception as e:
        print(f"ast-grep解析失败 {file_path}: {str(e)}", file=sys.stderr)
        return functions
    
    call_nodes = node.find_all(kind="call_expression")
    
    for call_node in call_nodes:
        try:
            text = call_node.text()
            if 'mg_set_request_handler' in text:
                import re
                match = re.search(r'mg_set_request_handler\s*\(\s*[^,]+,\s*[^,]+,\s*([a-zA-Z_][a-zA-Z0-9_]*)', text)
                if match:
                    callback_name = match.group(1)
                    callback_start = match.start(1)
                    
                    rng = call_node.range()
                    line_num = rng.start.line + 1
                    char_num = rng.start.column + callback_start + 1
                    
                    if lsp_client:
                        callback_info = _find_function_definition_with_lsp(
                            file_path, callback_name, line_num, char_num, code_dir, lsp_client
                        )
                    else:
                        callback_info = None
                    
                    if callback_info:
                        functions.append(callback_info)
        except Exception as e:
            print(f"处理调用节点失败: {str(e)}", file=sys.stderr)
            continue
    
    return functions


def _find_function_definition_with_lsp(file_path: str, callback_name: str, line: int, char: int, code_dir: str, lsp_client: LSPClient) -> FunctionInfo:
    """
    使用LSP查找回调函数定义位置
    """
    try:
        lsp_client.open_document(file_path, "c")
        
        definitions = lsp_client.get_definition(file_path, line, char)
        
        if not definitions or len(definitions) == 0:
            print(f"LSP未找到定义: {callback_name}", file=sys.stderr)
            return None
        
        def_info = definitions[0]
        uri = def_info.get('uri', '')
        
        if not uri:
            print(f"LSP返回的URI为空", file=sys.stderr)
            return None
        
        if uri.startswith('file://'):
            def_file_path = str(Path(uri[7:]))
        else:
            def_file_path = uri
        
        if not os.path.exists(def_file_path):
            print(f"定义文件不存在: {def_file_path}", file=sys.stderr)
            return None
        
        code_snippet = _extract_function_code_from_file(def_file_path, callback_name)
        
        rel_path = os.path.relpath(def_file_path, code_dir)
        
        return FunctionInfo(
            file_path=rel_path,
            function_name=callback_name,
            code_snippet=code_snippet
        )
    except Exception as e:
        print(f"通过LSP查找函数定义失败: {str(e)}", file=sys.stderr)
        return None





def _extract_function_code_from_file(file_path: str, function_name: str) -> str:
    """
    从文件中提取函数完整代码，包含行号
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        import re
        pattern = r'(?:void|int|char\s*\*|const\s+char\s*\*|size_t|static|unsigned|long)\s+' + re.escape(function_name) + r'\s*\('
        
        for i, line in enumerate(lines):
            if re.search(pattern, line):
                start_line = i + 1
                brace_count = 0
                found_open_brace = False
                end_line = start_line
                
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{')
                    brace_count -= lines[j].count('}')
                    
                    if '{' in lines[j]:
                        found_open_brace = True
                    
                    if found_open_brace and brace_count == 0:
                        end_line = j + 1
                        break
                
                code_lines = lines[start_line - 1:end_line]
                code_with_line_numbers = []
                for k, code_line in enumerate(code_lines, start=start_line):
                    code_with_line_numbers.append(f"{k:4d}: {code_line}")
                
                return ''.join(code_with_line_numbers).rstrip()
        
        return ""
    except Exception as e:
        print(f"提取函数代码失败 {file_path}: {str(e)}", file=sys.stderr)
        return ""


def _extract_function_code(file_path: str, start_line: int, end_line: int) -> str:
    """
    提取函数代码，包含行号
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        code_lines = lines[start_line - 1:end_line]
        code_with_line_numbers = []
        for i, line in enumerate(code_lines, start=start_line):
            code_with_line_numbers.append(f"{i:4d}: {line}")
        
        return ''.join(code_with_line_numbers).rstrip()
    except Exception as e:
        print(f"提取函数代码失败 {file_path}: {str(e)}", file=sys.stderr)
        return ""




if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python scan.py <代码目录>", file=sys.stderr)
        sys.exit(1)
    
    code_dir = sys.argv[1]
    
    if not os.path.exists(code_dir):
        print(f"目录不存在: {code_dir}", file=sys.stderr)
        sys.exit(1)
    
    functions = scan(code_dir)
    
    from dataclasses import asdict
    functions_dict = [asdict(func) for func in functions]
    print(json.dumps(functions_dict, indent=2, ensure_ascii=False))
