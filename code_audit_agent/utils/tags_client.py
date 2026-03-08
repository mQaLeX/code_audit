import os
import subprocess
import re
from typing import Optional, List, Dict, Any


class TagsClient:
    def __init__(self, workspace_root: Optional[str] = None, docker_manager=None):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.tags_file = os.path.join(self.workspace_root, "tags")
        self.cscope_out = os.path.join(self.workspace_root, "cscope.out")
        self.cscope_inouts = os.path.join(self.workspace_root, "cscope.in.out")
        self.cscope_po = os.path.join(self.workspace_root, "cscope.po.out")
        self._db_initialized = False
        self.docker_manager = docker_manager

    def is_available(self) -> bool:
        """检查 ctags 和 cscope 是否可用"""
        if self.docker_manager and self.docker_manager.container_id:
            result = self.docker_manager.execute_in_container("which ctags && which cscope", timeout=10)
            return result.get("success", False)
        
        try:
            subprocess.run(["ctags", "--version"], capture_output=True, check=True)
            subprocess.run(["cscope", "--version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def initialize(self) -> bool:
        """初始化符号数据库"""
        if not self.is_available():
            print("[WARN] ctags 或 cscope 不可用", file=__import__("sys").stderr)
            return False

        try:
            self._build_ctags()
            self._build_cscope()
            self._db_initialized = True
            return True
        except Exception as e:
            print(f"[ERROR] 初始化符号数据库失败: {str(e)}", file=__import__("sys").stderr)
            return False

    def _build_ctags(self):
        """使用 ctags 生成 tags 文件"""
        exclude_patterns = [
            "node_modules", ".git", "__pycache__", "build", "dist",
            ".venv", "venv", "target", "bin", "obj", "*.o", "*.a"
        ]
        exclude_args = []
        for pattern in exclude_patterns:
            exclude_args.extend(["--exclude=*" + pattern])

        cmd = [
            "ctags",
            "-R",
            "--languages=C,C++,Python,Java,Go,Rust",
            "--fields=+K",
            "-a",
            "tags"
        ] + exclude_args + ["."]

        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            cmd_str = f"cd {container_code_dir} && {' '.join(cmd)}"
            self.docker_manager.execute_in_container(cmd_str, timeout=120)
        else:
            subprocess.run(cmd, capture_output=True, timeout=120, cwd=self.workspace_root)

    def _build_cscope(self):
        """使用 cscope 生成交叉引用数据库"""
        extensions = ["c", "h", "cpp", "hpp", "cc", "cxx", "py", "js", "ts", "java", "go", "rs", "rb", "php"]
        file_list = "\n".join(f"*.{ext}" for ext in extensions)

        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            cmd = f"cd {container_code_dir} && cscope -b -q -k -i -"
            self.docker_manager.execute_in_container(cmd, timeout=120, input_data=file_list)
        else:
            subprocess.run(
                ["cscope", "-b", "-q", "-k", "-i", "-"],
                input=file_list,
                cwd=self.workspace_root,
                capture_output=True,
                timeout=120,
                text=True
            )

    def find_definition(self, symbol: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """使用 ctags 查找符号定义"""
        tags_file = "tags"
        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            container_tags_file = f"{container_code_dir}/tags"
            check_cmd = f"test -f {container_tags_file}"
            check_result = self.docker_manager.execute_in_container(check_cmd, timeout=10)
            if not check_result.get("success"):
                return []
            
            update_cmd = f"cd {container_code_dir} && ctags -a -u -R -n --fields=+K tags"
            self.docker_manager.execute_in_container(update_cmd, timeout=30)
            
            cat_result = self.docker_manager.execute_in_container(f"cat {container_tags_file}", timeout=10)
            if not cat_result.get("success"):
                return []
            
            return self._parse_tags_output(cat_result["stdout"], symbol, file_path)
        
        if not os.path.exists(self.tags_file):
            return []

        results = []
        try:
            cmd = ["ctags", "-a", "-u", "-R", "-n", "--fields=+K", self.tags_file]
            subprocess.run(cmd, capture_output=True, timeout=30)

            with open(self.tags_file, 'r', encoding='utf-8', errors='ignore') as f:
                return self._parse_tags_file(f, symbol, file_path)

        except Exception as e:
            print(f"[ERROR] ctags 查找失败: {str(e)}", file=__import__("sys").stderr)

        return results

    def _parse_tags_output(self, content: str, symbol: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """解析 ctags 输出"""
        results = []
        for line in content.split("\n"):
            if line.startswith("!"):
                continue
            
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            
            tag_name = parts[0]
            tag_file = parts[1]
            tag_pattern = parts[2]
            
            if symbol and symbol.lower() not in tag_name.lower():
                continue
            
            if file_path and not self._file_matches(tag_file, file_path):
                continue
            
            line_num = self._extract_line_number(tag_pattern)
            
            results.append({
                "file": tag_file,
                "line": line_num,
                "name": tag_name,
                "pattern": tag_pattern
            })
        
        return results

    def _parse_tags_file(self, f, symbol: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """解析 ctags 文件"""
        results = []
        for line in f:
            if line.startswith("!"):
                continue
            
            parts = line.strip().split("\t")
            if len(parts) < 3:
                continue
            
            tag_name = parts[0]
            tag_file = parts[1]
            tag_pattern = parts[2]
            
            if symbol and symbol.lower() not in tag_name.lower():
                continue
            
            if file_path and not self._file_matches(tag_file, file_path):
                continue
            
            line_num = self._extract_line_number(tag_pattern)
            
            results.append({
                "file": tag_file,
                "line": line_num,
                "name": tag_name,
                "pattern": tag_pattern
            })
        
        return results

    def find_references(self, symbol: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """使用 cscope 查找符号引用"""
        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            container_cscope_out = f"{container_code_dir}/cscope.out"
            check_cmd = f"test -f {container_cscope_out}"
            check_result = self.docker_manager.execute_in_container(check_cmd, timeout=10)
            if not check_result.get("success"):
                return []
            
            cmd = f"cd {container_code_dir} && cscope -d -L -0 {symbol}"
            result = self.docker_manager.execute_in_container(cmd, timeout=30)
            if not result.get("success"):
                return []
            
            return self._parse_cscope_output(result["stdout"], symbol, file_path)
        
        if not os.path.exists(self.cscope_out):
            return []

        results = []
        try:
            cmd = ["cscope", "-d", "-L", "-0", symbol]
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            return self._parse_cscope_output(proc.stdout, symbol, file_path)

        except Exception as e:
            print(f"[ERROR] cscope 查找失败: {str(e)}", file=__import__("sys").stderr)

        return results

    def _parse_cscope_output(self, output: str, symbol: str, file_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """解析 cscope 输出"""
        results = []
        for line in output.strip().split("\n"):
            if not line:
                continue
            
            parts = line.split(None, 3)
            if len(parts) < 4:
                continue
            
            ref_file = parts[0]
            ref_line = int(parts[1])
            ref_context = parts[3] if len(parts) > 3 else ""
            
            if file_path and not self._file_matches(ref_file, file_path):
                continue
            
            results.append({
                "file": ref_file,
                "line": ref_line,
                "context": ref_context.strip()
            })
        
        return results

    def find_symbol_definition(self, symbol: str) -> List[Dict[str, Any]]:
        """使用 cscope 查找符号定义 (模式 1)"""
        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            container_cscope_out = f"{container_code_dir}/cscope.out"
            check_cmd = f"test -f {container_cscope_out}"
            check_result = self.docker_manager.execute_in_container(check_cmd, timeout=10)
            if not check_result.get("success"):
                return []
            
            cmd = f"cd {container_code_dir} && cscope -d -L -1 {symbol}"
            result = self.docker_manager.execute_in_container(cmd, timeout=30)
            if not result.get("success"):
                return []
            
            return self._parse_cscope_output(result["stdout"], symbol)
        
        if not os.path.exists(self.cscope_out):
            return []

        results = []
        try:
            cmd = ["cscope", "-d", "-L", "-1", symbol]
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            return self._parse_cscope_output(proc.stdout, symbol)

        except Exception as e:
            print(f"[ERROR] cscope 查找定义失败: {str(e)}", file=__import__("sys").stderr)

        return results

    def find_calling(self, symbol: str) -> List[Dict[str, Any]]:
        """使用 cscope 查找被该函数调用的函数 (模式 3)"""
        if self.docker_manager and self.docker_manager.container_id:
            container_code_dir = self.docker_manager.get_code_dir_in_container()
            container_cscope_out = f"{container_code_dir}/cscope.out"
            check_cmd = f"test -f {container_cscope_out}"
            check_result = self.docker_manager.execute_in_container(check_cmd, timeout=10)
            if not check_result.get("success"):
                return []
            
            cmd = f"cd {container_code_dir} && cscope -d -L -3 {symbol}"
            result = self.docker_manager.execute_in_container(cmd, timeout=30)
            if not result.get("success"):
                return []
            
            return self._parse_cscope_output(result["stdout"], symbol)
        
        if not os.path.exists(self.cscope_out):
            return []

        results = []
        try:
            cmd = ["cscope", "-d", "-L", "-3", symbol]
            proc = subprocess.run(
                cmd,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=30
            )

            return self._parse_cscope_output(proc.stdout, symbol)

        except Exception as e:
            print(f"[ERROR] cscope 查找调用失败: {str(e)}", file=__import__("sys").stderr)

        return results

    def _extract_line_number(self, pattern: str) -> int:
        """从 ctags 模式中提取行号"""
        match = re.search(r'/^([^/]+)/$', pattern)
        if match:
            return 1

        match = re.search(r';"$', pattern)
        if match:
            pattern = pattern[:match.start()]
            parts = pattern.rsplit(";", 1)
            if len(parts) > 1:
                try:
                    return int(parts[-1])
                except ValueError:
                    pass

        return 1

    def _file_matches(self, db_file: str, input_file: str) -> bool:
        """检查数据库中的文件是否匹配输入文件"""
        db_file = os.path.abspath(db_file)
        input_file = os.path.abspath(input_file)
        return os.path.basename(db_file) == os.path.basename(input_file)

    def rebuild(self) -> bool:
        """重建符号数据库"""
        self._cleanup()
        return self.initialize()

    def _cleanup(self):
        """清理生成的数据库文件"""
        for f in [self.tags_file, self.cscope_out, self.cscope_inouts, self.cscope_po]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass
