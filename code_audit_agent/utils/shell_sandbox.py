import os
import subprocess
import re
import json
import shlex
import select
import time
import uuid
from typing import Dict, Any, Optional, Tuple


class ShellSandbox:
    """Shell 沙盒，在指定目录执行命令，维护会话状态"""
    
    def __init__(self, code_dir: str, timeout: int = 60, docker_manager=None):
        self.code_dir = os.path.abspath(code_dir)
        self.timeout = timeout
        self.env = os.environ.copy()
        self.env["PYTHONUNBUFFERED"] = "1"
        
        self.process: Optional[subprocess.Popen] = None
        self.cwd = code_dir
        self.docker_manager = docker_manager
        
        self.dangerous_patterns = [
            r'\.\./',  
            r'/\.\.',  
            r'^/etc',
            r'^/root',
            r'^/usr/bin/(rm|mv|cp|chmod|chown)\s',
            r';\s*rm\s+',
            r'&&\s*rm\s+',
            r'\|\s*rm\s+',
            r'>\s*/dev/',
            r'2>\s*/dev/',
        ]
        
        self._start_shell()
    
    def _start_shell(self):
        """启动持久化的 bash 会话"""
        if self.docker_manager and self.docker_manager.container_id:
            self._start_docker_shell()
        else:
            self._start_local_shell()
    
    def _start_local_shell(self):
        """启动本地 bash 会话"""
        self.process = subprocess.Popen(
            ["bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            env=self.env,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
    
    def _start_docker_shell(self):
        """启动 Docker 容器内的 bash 会话"""
        container_code_dir = self.docker_manager.get_code_dir_in_container()
        
        cmd = f"docker exec -it {self.docker_manager.container_id} bash"
        self.process = subprocess.Popen(
            cmd,
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.code_dir,
            env=self.env,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )
    
    def _check_path_safety(self, cmd: str) -> Tuple[bool, str]:
        """检查路径安全性"""
        if 'cd' in cmd:
            cd_match = re.search(r'cd\s+["\']?([^"\'\s;]+)', cmd)
            if cd_match:
                target_path = cd_match.group(1)
                
                if target_path.startswith('/'):
                    abs_path = os.path.abspath(target_path)
                else:
                    abs_path = os.path.abspath(os.path.join(self.code_dir, target_path))
                
                if not abs_path.startswith(self.code_dir):
                    return False, f"路径 {target_path} 超出代码目录范围"
                
                if '..' in target_path:
                    abs_path = os.path.abspath(os.path.join(self.code_dir, target_path))
                    if not abs_path.startswith(self.code_dir):
                        return False, f"路径 {target_path} 尝试跳出代码目录"
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, cmd):
                return False, f"命令包含危险模式: {pattern}"
        
        return True, ""
    
    def _resolve_path(self, path: str) -> str:
        """解析路径为绝对路径"""
        if path.startswith('/'):
            return os.path.abspath(path)
        return os.path.abspath(os.path.join(self.code_dir, path))
    
    def execute(self, cmd: str) -> Dict[str, Any]:
        """
        执行 shell 命令（通过持久会话）
        返回: {"success": bool, "stdout": str, "stderr": str, "returncode": int}
        """
        is_safe, error_msg = self._check_path_safety(cmd)
        if not is_safe:
            return {
                "success": False,
                "stdout": "",
                "stderr": error_msg,
                "returncode": 1,
                "error": error_msg
            }
        
        if self.docker_manager and self.docker_manager.container_id:
            return self._execute_in_docker(cmd)
        
        return self._execute_local(cmd)
    
    def _execute_local(self, cmd: str) -> Dict[str, Any]:
        """在本地执行命令"""
        if not self.process or self.process.poll() is not None:
            self._start_shell()
        
        try:
            marker = f"__CMD_DONE_{uuid.uuid4().hex}__"
            
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.write(f"echo {marker}$?\n")
            self.process.stdin.flush()
            
            output_lines = []
            error_lines = []
            returncode = 0
            
            start_time = time.time()
            command_done = False
            
            while True:
                if time.time() - start_time > self.timeout:
                    return {
                        "success": False,
                        "stdout": "\n".join(output_lines),
                        "stderr": f"命令执行超时 ({self.timeout}秒)",
                        "returncode": -1,
                        "error": "timeout"
                    }
                
                ready, _, _ = select.select([self.process.stdout, self.process.stderr], [], [], 0.1)
                
                if not ready and self.process.poll() is not None:
                    break
                
                for stream in ready:
                    if stream == self.process.stdout:
                        line = self.process.stdout.readline()
                        if line:
                            line = line.rstrip()
                            if marker in line:
                                try:
                                    returncode = int(line.split(marker)[1])
                                except:
                                    pass
                                command_done = True
                            else:
                                output_lines.append(line)
                    elif stream == self.process.stderr:
                        line = self.process.stderr.readline()
                        if line:
                            error_lines.append(line.rstrip())
                
                if command_done:
                    break
            
            stdout = "\n".join(output_lines)
            stdout = stdout.replace(marker + str(returncode), "").strip()
            stderr = "\n".join(error_lines)
            
            if cmd.strip().startswith("cd "):
                cd_match = re.search(r'cd\s+["\']?([^"\'\s;]+)', cmd)
                if cd_match:
                    new_path = cd_match.group(1)
                    if new_path.startswith('/'):
                        check_path = new_path
                    else:
                        check_path = os.path.join(self.cwd, new_path)
                    if os.path.isdir(check_path):
                        self.cwd = os.path.abspath(check_path)
            
            return {
                "success": returncode == 0,
                "stdout": stdout,
                "stderr": stderr,
                "returncode": returncode
            }
            
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
                "error": str(e)
            }
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """
        执行 Python 代码
        返回: {"success": bool, "stdout": str, "stderr": str, "returncode": int}
        """
        if self.docker_manager and self.docker_manager.container_id:
            return self._execute_python_in_docker(code)
        
        return self._execute_python_local(code)
    
    def _execute_python_local(self, code: str) -> Dict[str, Any]:
        """在本地执行 Python 代码"""
        try:
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=self.timeout,
                cwd=self.code_dir,
                env=self.env
            )
            
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Python执行超时 ({self.timeout}秒)",
                "returncode": -1,
                "error": "timeout"
            }
    
    def _execute_python_in_docker(self, code: str) -> Dict[str, Any]:
        """在 Docker 容器内执行 Python 代码"""
        escaped_code = code.replace("'", "'\\''")
        cmd = f"python3 -c '{escaped_code}'"
        return self.docker_manager.execute_in_container(cmd, self.timeout)
    
    def _execute_in_docker(self, cmd: str) -> Dict[str, Any]:
        """在 Docker 容器内执行命令"""
        container_code_dir = self.docker_manager.get_code_dir_in_container()
        full_cmd = f"cd {container_code_dir} && {cmd}"
        return self.docker_manager.execute_in_container(full_cmd, self.timeout)
    
    def call_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """
        统一工具调用接口
        tool_call: {"type": "shell"|"python", "command": str}
        """
        tool_type = tool_call.get("type", "shell")
        command = tool_call.get("command", "")
        
        if not command:
            return {
                "success": False,
                "stdout": "",
                "stderr": "命令不能为空",
                "returncode": 1
            }
        
        if tool_type == "python":
            return self.execute_python(command)
        else:
            return self.execute(command)
    
    def get_info(self) -> Dict[str, Any]:
        """获取沙盒信息"""
        return {
            "code_dir": self.code_dir,
            "cwd": self.cwd,
            "timeout": self.timeout
        }
    
    def close(self):
        """关闭 shell 会话"""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
    
    def __del__(self):
        self.close()
