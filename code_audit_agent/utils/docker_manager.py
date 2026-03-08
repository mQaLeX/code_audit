import os
import subprocess
import shutil
import time
from typing import Optional, Dict, Any
from pathlib import Path


class DockerManager:
    def __init__(self, docker_image: str, code_dir: str):
        self.docker_image = docker_image
        self.code_dir = os.path.abspath(code_dir)
        self.container_id: Optional[str] = None
        self.container_code_dir: Optional[str] = None
        self._container_name: Optional[str] = None

    def pull_image(self) -> bool:
        print(f"[Docker] 正在拉取镜像: {self.docker_image}")
        try:
            result = subprocess.run(
                ["docker", "pull", self.docker_image],
                capture_output=True,
                text=True,
                timeout=600
            )
            if result.returncode != 0:
                print(f"[Docker] 拉取镜像失败: {result.stderr}")
                return False
            print(f"[Docker] 镜像拉取成功")
            return True
        except subprocess.TimeoutExpired:
            print(f"[Docker] 拉取镜像超时")
            return False
        except FileNotFoundError:
            print(f"[Docker] Docker未安装或不在PATH中")
            return False
        except Exception as e:
            print(f"[Docker] 拉取镜像失败: {str(e)}")
            return False

    def create_container(self) -> bool:
        container_name = f"code_audit_{int(time.time())}"
        
        volume_bind = f"{self.code_dir}:/code"
        
        try:
            result = subprocess.run(
                [
                    "docker", "create",
                    "--name", container_name,
                    "-v", volume_bind,
                    "-w", "/code",
                    "-it", self.docker_image,
                    "/bin/bash"
                ],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"[Docker] 创建容器失败: {result.stderr}")
                return False
            
            self.container_id = result.stdout.strip()
            self._container_name = container_name
            self.container_code_dir = "/code"
            
            print(f"[Docker] 容器创建成功: {self.container_id}")
            return True
        except Exception as e:
            print(f"[Docker] 创建容器失败: {str(e)}")
            return False

    def start_container(self) -> bool:
        if not self.container_id:
            print(f"[Docker] 错误: 容器未创建")
            return False
        
        try:
            result = subprocess.run(
                ["docker", "start", self.container_id],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"[Docker] 启动容器失败: {result.stderr}")
                return False
            
            print(f"[Docker] 容器已启动: {self.container_id}")
            return True
        except Exception as e:
            print(f"[Docker] 启动容器失败: {str(e)}")
            return False

    def stop_container(self) -> bool:
        if not self.container_id:
            return True
        
        try:
            subprocess.run(
                ["docker", "stop", self.container_id],
                capture_output=True,
                text=True,
                timeout=60
            )
            print(f"[Docker] 容器已停止: {self.container_id}")
            return True
        except Exception as e:
            print(f"[Docker] 停止容器失败: {str(e)}")
            return False

    def remove_container(self) -> bool:
        if not self.container_id:
            return True
        
        try:
            subprocess.run(
                ["docker", "rm", "-f", self.container_id],
                capture_output=True,
                text=True,
                timeout=60
            )
            print(f"[Docker] 容器已删除: {self.container_id}")
            self.container_id = None
            return True
        except Exception as e:
            print(f"[Docker] 删除容器失败: {str(e)}")
            return False

    def execute_in_container(self, command: str, timeout: int = 60, input_data: str = None) -> Dict[str, Any]:
        if not self.container_id:
            return {
                "success": False,
                "stdout": "",
                "stderr": "容器未启动",
                "returncode": -1
            }
        
        try:
            result = subprocess.run(
                ["docker", "exec", self.container_id, "bash", "-c", command],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.code_dir
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
                "stderr": f"命令执行超时 ({timeout}秒)",
                "returncode": -1
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1
            }

    def execute_python_in_container(self, code: str, timeout: int = 60) -> Dict[str, Any]:
        escaped_code = code.replace("'", "'\\''")
        
        python_cmd = f"python3 -c '{escaped_code}'"
        
        return self.execute_in_container(python_cmd, timeout)

    def get_container_info(self) -> Dict[str, Any]:
        if not self.container_id:
            return {}
        
        try:
            result = subprocess.run(
                ["docker", "inspect", self.container_id],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                if info:
                    return info[0]
        except Exception:
            pass
        
        return {}

    def is_container_running(self) -> bool:
        if not self.container_id:
            return False
        
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Running}}", self.container_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip().lower() == "true"
        except Exception:
            return False

    def get_container_ip(self) -> Optional[str]:
        if not self.container_id:
            return None
        
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.NetworkSettings.IPAddress}}", self.container_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            ip = result.stdout.strip()
            return ip if ip else None
        except Exception:
            return None

    def setup(self) -> bool:
        if not self.pull_image():
            return False
        
        if not self.create_container():
            return False
        
        if not self.start_container():
            self.remove_container()
            return False
        
        return True

    def cleanup(self):
        self.stop_container()
        self.remove_container()

    def get_code_dir_in_container(self) -> str:
        return self.container_code_dir or "/code"

    @staticmethod
    def check_docker_available() -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
