import json
import subprocess
import os
from typing import Optional, List, Dict, Any
from pathlib import Path


class LSPClient:
    def __init__(self, workspace_root: Optional[str] = None, compile_json_path: str = None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.process = None
        self.request_id = 0
        self._available = False
        self.compile_json_path = None
        
        if compile_json_path == None:
            compile_json_path = os.path.join(self.workspace_root, 'compile_commands.json')
            if os.path.exists(compile_json_path):
                self.compile_json_path = compile_json_path
                self._available = True
            else:
                for dir in os.listdir(self.workspace_root):
                    compile_json_path = os.path.join(self.workspace_root, dir, 'compile_commands.json')
                    if os.path.isdir(os.path.join(self.workspace_root, dir)) and os.path.exists(compile_json_path):
                        self.compile_json_path = compile_json_path
                        self._available = True
                        break
                else:
                    print(f"[WARN] 未找到compile_commands.json文件，LSP功能将受限")
                    compile_json_path = None
        else:
            if os.path.exists(compile_json_path):
                self.compile_json_path = compile_json_path
                self._available = True
            else:
                print(f"[WARN] 指定的compile_commands.json文件不存在: {compile_json_path}")
    
    def is_available(self) -> bool:
        """检查LSP是否可用（有compile_commands.json）"""
        return self._available

    def start(self) -> bool:
        if not self._available:
            print(f"[WARN] LSP不可用：缺少compile_commands.json")
            return False
        
        try:
            self.process = subprocess.Popen(
                'clangd',
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.workspace_root,
                bufsize=0
            )
            return self.process.poll() is None
        except Exception as e:
            print(f"启动LSP服务器失败: {str(e)}")
            return False

    def stop(self):
        if self.process:
            self._send_notification("exit", {})
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.terminate()

    def _send_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.process or self.process.poll() is not None:
            return None

        content = json.dumps(message)
        header = f"Content-Length: {len(content)}\r\n\r\n"
        full_message = header + content

        try:
            self.process.stdin.write(full_message.encode('utf-8'))
            self.process.stdin.flush()

            if 'id' in message:
                return self._read_response()
        except Exception as e:
            print(f"LSP请求失败: {str(e)}")

        return None

    def _read_response(self) -> Optional[Dict[str, Any]]:
        while True:
            headers = b''
            while True:
                line = self.process.stdout.readline()
                headers += line
                if line == b'\r\n':
                    break

            content_length = 0
            for line in headers.decode('utf-8').split('\r\n'):
                if line.startswith('Content-Length:'):
                    content_length = int(line.split(':')[1].strip())

            if content_length == 0:
                return None

            content = self.process.stdout.read(content_length)
            response = json.loads(content.decode('utf-8'))

            if 'method' in response and 'id' not in response:
                continue

            return response

    def _send_request(self, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        self.request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params
        }
        response = self._send_message(request)
        if response:
            if "result" in response:
                return response["result"]
            elif "error" in response:
                print(f"LSP错误: {response['error']}")
        return None

    def _send_notification(self, method: str, params: Dict[str, Any]):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        self._send_message(notification)

    def initialize(self) -> bool:
        params = {
            "processId": os.getpid(),
            "rootUri": Path(self.workspace_root).as_uri(),
            "capabilities": {
                "textDocument": {
                    "hover": {"contentFormat": ["markdown", "plaintext"]},
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "documentSymbol": {"dynamicRegistration": True}
                }
            }
        }
        result = self._send_request("initialize", params)
        if result:
            self._send_notification("initialized", {})
            return True
        return False

    def open_document(self, file_path: str, language_id: str = "cpp") -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            print(f"读取文件失败: {str(e)}")
            return False

        params = {
            "textDocument": {
                "uri": Path(file_path).as_uri(),
                "languageId": language_id,
                "version": 1,
                "text": content
            }
        }
        self._send_notification("textDocument/didOpen", params)
        return True

    def get_definition(self, file_path: str, line: int, character: int) -> Optional[List[Dict[str, Any]]]:
        params = {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line - 1, "character": character - 1}
        }
        return self._send_request("textDocument/definition", params)

    def get_references(self, file_path: str, line: int, character: int) -> Optional[List[Dict[str, Any]]]:
        params = {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line - 1, "character": character - 1},
            "context": {"includeDeclaration": True}
        }
        return self._send_request("textDocument/references", params)

    def get_document_symbols(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        params = {
            "textDocument": {"uri": Path(file_path).as_uri()}
        }
        return self._send_request("textDocument/documentSymbol", params)

    def get_hover(self, file_path: str, line: int, character: int) -> Optional[Dict[str, Any]]:
        params = {
            "textDocument": {"uri": Path(file_path).as_uri()},
            "position": {"line": line - 1, "character": character - 1}
        }
        return self._send_request("textDocument/hover", params)

    def get_code_context(self, file_path: str, line_start: int, line_end: int) -> List[Dict[str, Any]]:
        contexts = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num in range(line_start, line_end + 1):
                if line_num <= len(lines):
                    line_content = lines[line_num - 1]

                    for char_pos, char in enumerate(line_content):
                        if char.isalpha() or char == '_':
                            definition = self.get_definition(file_path, line_num, char_pos + 1)
                            if definition:
                                contexts.append({
                                    "type": "definition",
                                    "line": line_num,
                                    "character": char_pos + 1,
                                    "result": definition
                                })

                            references = self.get_references(file_path, line_num, char_pos + 1)
                            if references:
                                contexts.append({
                                    "type": "references",
                                    "line": line_num,
                                    "character": char_pos + 1,
                                    "result": references
                                })
                            break
        except Exception as e:
            print(f"获取代码上下文失败: {str(e)}")

        return contexts

    def get_function_calls(self, file_path: str, line_start: int, line_end: int) -> List[Dict[str, Any]]:
        calls = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            for line_num in range(line_start, line_end + 1):
                if line_num <= len(lines):
                    line_content = lines[line_num - 1]

                    for char_pos, char in enumerate(line_content):
                        if char.isalpha() or char == '_':
                            definition = self.get_definition(file_path, line_num, char_pos + 1)
                            if definition and len(definition) > 0:
                                def_info = definition[0]
                                if 'range' in def_info:
                                    calls.append({
                                        "line": line_num,
                                        "character": char_pos + 1,
                                        "definition": def_info
                                    })
                            break
        except Exception as e:
            print(f"获取函数调用失败: {str(e)}")

        return calls

    def get_all_symbols(self, file_path: str) -> List[Dict[str, Any]]:
        symbols = self.get_document_symbols(file_path)
        if not symbols:
            return []

        all_symbols = []

        def extract_symbols(symbols_list):
            for symbol in symbols_list:
                all_symbols.append({
                    "name": symbol.get("name", ""),
                    "kind": symbol.get("kind", 0),
                    "detail": symbol.get("detail", ""),
                    "range": symbol.get("range"),
                    "selectionRange": symbol.get("selectionRange")
                })
                if "children" in symbol:
                    extract_symbols(symbol["children"])

        extract_symbols(symbols)
        return all_symbols

    def __enter__(self):
        if self.start():
            self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
