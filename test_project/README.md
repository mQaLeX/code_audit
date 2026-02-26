# 测试项目

这是一个包含安全漏洞的Flask测试应用，用于验证代码审计Agent的功能。

## 漏洞列表

### 1. 命令注入漏洞

#### /ping 端点
- **漏洞类型**: 命令注入
- **位置**: app.py 第24行
- **描述**: 使用 `os.popen()` 直接执行用户输入的命令
- **利用方式**: `?host=127.0.0.1;whoami` 或 `?host=127.0.0.1|cat /etc/passwd`

#### /exec 端点
- **漏洞类型**: 命令注入
- **位置**: app.py 第51行
- **描述**: 使用 `os.system()` 直接执行用户输入的命令
- **利用方式**: `?cmd=whoami` 或 `?cmd=cat /etc/passwd`

#### /search 端点
- **漏洞类型**: 命令注入
- **位置**: app.py 第68行
- **描述**: 使用 `grep` 命令时未过滤用户输入
- **利用方式**: `?q=test;whoami` 或 `?q=test|cat /etc/passwd`

### 2. 任意文件读取漏洞

#### /read 端点
- **漏洞类型**: 任意文件读取
- **位置**: app.py 第38行
- **描述**: 直接读取用户指定的文件路径，未进行路径验证
- **利用方式**: `?file=/etc/passwd` 或 `?file=../../../etc/passwd`

#### /download 端点
- **漏洞类型**: 任意文件读取
- **位置**: app.py 第85行
- **描述**: 直接下载用户指定的文件，未进行路径验证
- **利用方式**: `?path=/etc/passwd` 或 `?path=../../../etc/passwd`

#### /log 端点
- **漏洞类型**: 任意文件读取
- **位置**: app.py 第103行
- **描述**: 直接读取用户指定的日志文件，未进行路径验证
- **利用方式**: `?file=/etc/passwd` 或 `?file=../../../etc/passwd`

## 运行方式

```bash
# 安装依赖
pip install -r requirements.txt

# 启动应用
python app.py
```

应用将在 `http://localhost:5000` 上运行。

## 测试命令注入漏洞

```bash
# 测试 /ping 端点
curl "http://localhost:5000/ping?host=127.0.0.1;whoami"
curl "http://localhost:5000/ping?host=127.0.0.1|cat /etc/passwd"

# 测试 /exec 端点
curl "http://localhost:5000/exec?cmd=whoami"
curl "http://localhost:5000/exec?cmd=cat /etc/passwd"

# 测试 /search 端点
curl "http://localhost:5000/search?q=test;whoami"
curl "http://localhost:5000/search?q=test|cat /etc/passwd"
```

## 测试任意文件读取漏洞

```bash
# 测试 /read 端点
curl "http://localhost:5000/read?file=/etc/passwd"
curl "http://localhost:5000/read?file=../../../etc/passwd"

# 测试 /download 端点
curl "http://localhost:5000/download?path=/etc/passwd" -O

# 测试 /log 端点
curl "http://localhost:5000/log?file=/etc/passwd"
```

## 使用代码审计Agent进行测试

```bash
# 回到项目根目录
cd ..

# 运行代码审计
python main.py test_project python web --skip-exploit --verbose
```

## 预期结果

代码审计Agent应该能够发现以下漏洞：

1. **命令注入漏洞** (3个)
   - `/ping` 端点
   - `/exec` 端点
   - `/search` 端点

2. **任意文件读取漏洞** (3个)
   - `/read` 端点
   - `/download` 端点
   - `/log` 端点

## 注意事项

⚠️ **警告**: 此测试应用包含真实的安全漏洞，仅用于教育和测试目的。请勿在生产环境中使用或部署此应用。

⚠️ **安全提示**: 在运行此应用时，请确保：
1. 仅在本地测试环境中运行
2. 不要暴露在公网上
3. 测试完成后及时停止应用

## 修复建议

### 命令注入漏洞修复

使用 `subprocess` 模块并避免直接拼接用户输入：

```python
import subprocess

# 错误的方式
command = f"ping -c {count} {host}"
os.popen(command)

# 正确的方式
subprocess.run(['ping', '-c', count, host], check=True)
```

### 任意文件读取漏洞修复

验证和规范化文件路径：

```python
import os

# 错误的方式
with open(filename, 'r') as f:
    content = f.read()

# 正确的方式
safe_path = os.path.normpath(filename)
if not safe_path.startswith('/allowed/directory'):
    raise ValueError("不允许的文件路径")
with open(safe_path, 'r') as f:
    content = f.read()
```
