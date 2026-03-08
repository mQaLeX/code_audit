# Code Audit Agent Docker Environment

用于代码审计的 Docker 镜像，包含完整的渗透测试工具链和开发环境。

## 镜像内容

### 基础环境
- Ubuntu 22.04
- 中国镜像源（清华大学镜像）
- Python 3 (pip 使用清华源)

### C/C++ 开发工具
- GCC/G++ (build-essential)
- Clang/LLVM
- CMake, Autoconf, Automake
- GDB (调试器)
- Valgrind (内存检测)
- clangd (LSP 服务器)

### 代码分析工具
- ctags (符号索引)
- cscope (代码浏览)
- global (GNU Global)

### 渗透测试工具
- netcat (网络工具)
- nmap (端口扫描)
- tcpdump (抓包)
- wireshark-cli (协议分析)
- radare2 (逆向分析)
- binwalk (固件分析)

### Python 安全库
- pwntools (CTF 框架)
- angr (符号执行)
- z3-solver (SMT 求解器)
- pycryptodome (加密库)
- capstone (反汇编)
- ropper (ROP 工具)

### 常用开发库
- libssl-dev (OpenSSL)
- libffi-dev (FFI)
- libcurl4-openssl-dev (HTTP)
- libpcap-dev (网络抓包)
- libevent-dev (事件驱动)

## 构建镜像

```bash
# 进入目录
cd agent_docker

# 添加执行权限
chmod +x build.sh

# 构建镜像
./build.sh

# 或指定自定义名称和标签
./build.sh -n my-audit -t v1.0
```

## 使用方法

### 1. 与 code_audit 集成使用

```bash
# 使用 Docker 镜像启动代码审计
python main.py c civetweb /path/to/code --docker-image code-audit-agent:latest
```

### 2. 手动运行容器

```bash
# 交互式运行
docker run -it --rm \
    -v /path/to/your/code:/workspace \
    code-audit-agent:latest

# 后台运行
docker run -d \
    --name audit-env \
    -v /path/to/your/code:/workspace \
    code-audit-agent:latest

# 进入运行中的容器
docker exec -it audit-env /bin/bash
```

### 3. 挂载多个目录

```bash
docker run -it --rm \
    -v /path/to/code:/workspace \
    -v /path/to/output:/output \
    code-audit-agent:latest
```

## 工作目录

容器内默认工作目录为 `/workspace`，代码目录会挂载到此位置。

## 镜像大小

构建后镜像大小约 2-3GB，包含完整的开发和安全测试环境。

## 注意事项

1. 首次构建可能需要较长时间下载依赖
2. 使用中国镜像源加速下载
3. 容器内已配置好 clangd 和 ctags/cscope 环境
4. Python pip 已配置清华镜像源

## 自定义修改

如需添加其他工具，编辑 `Dockerfile` 后重新构建：

```dockerfile
# 在 apt-get install 部分添加
RUN apt-get update && apt-get install -y \
    your-package-name \
    ...

# 或添加 Python 包
RUN pip3 install --no-cache-dir \
    your-python-package \
    ...
```
