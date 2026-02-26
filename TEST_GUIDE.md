# 测试项目使用指南

## 概述

本测试项目包含一个故意设计的安全漏洞Flask应用，用于验证代码审计Agent的功能。该应用包含以下漏洞：

- **3个命令注入漏洞**
- **3个任意文件读取漏洞**

## 项目结构

```
test_project/
├── app.py              # 包含漏洞的Flask应用
├── requirements.txt    # 依赖文件
└── README.md          # 详细说明文档
```

## 漏洞详情

### 命令注入漏洞 (3个)

1. **`/ping` 端点** (app.py:24)
   - 使用 `os.popen()` 执行用户输入
   - 利用: `?host=127.0.0.1;whoami`

2. **`/exec` 端点** (app.py:51)
   - 使用 `os.system()` 执行用户输入
   - 利用: `?cmd=whoami`

3. **`/search` 端点** (app.py:68)
   - 使用 `grep` 命令时未过滤输入
   - 利用: `?q=test;whoami`

### 任意文件读取漏洞 (3个)

1. **`/read` 端点** (app.py:38)
   - 直接读取用户指定的文件
   - 利用: `?file=/etc/passwd`

2. **`/download` 端点** (app.py:85)
   - 直接下载用户指定的文件
   - 利用: `?path=/etc/passwd`

3. **`/log` 端点** (app.py:103)
   - 直接读取用户指定的日志文件
   - 利用: `?file=/etc/passwd`

## 快速开始

### 方法1: 使用自动化测试脚本

```bash
# 运行快速测试脚本
./quick_test.sh
```

这个脚本会：
1. 安装依赖
2. 检查环境变量
3. 运行代码审计
4. 生成报告

### 方法2: 手动运行审计

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置OpenAI API密钥
export OPENAI_API_KEY=your_api_key_here

# 3. 运行代码审计（跳过漏洞利用）
python main.py test_project python web --skip-exploit --verbose
```

### 方法3: 完整审计（包含漏洞利用）

```bash
# 运行完整审计（包含漏洞利用）
python main.py test_project python web --verbose
```

## 手动测试漏洞

如果你想手动验证漏洞是否可利用：

### 1. 启动测试应用

```bash
cd test_project
pip install -r requirements.txt
python app.py
```

应用将在 `http://localhost:5000` 上运行。

### 2. 在另一个终端运行手动测试

```bash
python manual_test.py
```

这将自动测试所有漏洞并显示结果。

### 3. 手动使用curl测试

```bash
# 测试命令注入
curl "http://localhost:5000/ping?host=127.0.0.1;whoami"
curl "http://localhost:5000/exec?cmd=whoami"
curl "http://localhost:5000/search?q=test;whoami"

# 测试任意文件读取
curl "http://localhost:5000/read?file=/etc/passwd"
curl "http://localhost:5000/download?path=/etc/passwd"
curl "http://localhost:5000/log?file=/etc/passwd"
```

## 预期结果

### 代码审计Agent应该发现：

- **6个接口函数**:
  1. `index()` - 首页
  2. `ping()` - Ping测试（命令注入）
  3. `read_file()` - 文件读取（任意文件读）
  4. `exec_command()` - 命令执行（命令注入）
  5. `search()` - 搜索（命令注入）
  6. `download_file()` - 文件下载（任意文件读）
  7. `view_log()` - 查看日志（任意文件读）

- **多个漏洞**:
  - 命令注入漏洞（至少3个）
  - 任意文件读取漏洞（至少3个）

### 生成的报告将包含：

1. **Markdown报告** (`security_report_web_*.md`)
2. **JSON报告** (`security_report_web_*.json`)
3. **HTML报告** (`security_report_web_*.html`)

每个报告包含：
- 漏洞类型
- 漏洞路径（文件和函数名）
- 漏洞详情
- 严重程度
- CVSS评分
- 漏洞影响
- 修复建议

## 测试场景

### 场景1: 仅审计（不利用漏洞）

```bash
python main.py test_project python web --skip-exploit --verbose
```

适用情况：
- 快速扫描代码
- 了解潜在漏洞
- 不需要实际验证漏洞

### 场景2: 完整审计（包含漏洞利用）

```bash
python main.py test_project python web --verbose
```

适用情况：
- 需要验证漏洞是否可利用
- 生成完整的漏洞报告
- 包含利用脚本和截图

### 场景3: 自定义并发数

```bash
python main.py test_project python web --max-workers 10 --verbose
```

适用情况：
- 加快审计速度
- 有足够的API配额

### 场景4: 指定报告格式

```bash
# 只生成Markdown报告
python main.py test_project python web --report-format markdown

# 只生成JSON报告
python main.py test_project python web --report-format json

# 只生成HTML报告
python main.py test_project python web --report-format html
```

## 故障排除

### 问题1: OPENAI_API_KEY未设置

**错误信息**: `错误: LLM客户端初始化失败`

**解决方案**:
```bash
export OPENAI_API_KEY=your_api_key_here
```

或在运行时指定:
```bash
python main.py test_project python web --api-key your_api_key_here
```

### 问题2: 测试应用无法启动

**错误信息**: `Address already in use`

**解决方案**:
```bash
# 查找占用5000端口的进程
lsof -i :5000

# 杀死该进程
kill -9 <PID>
```

### 问题3: 扫描未发现函数

**可能原因**:
- 项目路径不正确
- 文件权限问题

**解决方案**:
```bash
# 检查项目路径
ls -la test_project/

# 确保app.py存在
cat test_project/app.py
```

### 问题4: 审计超时

**解决方案**:
- 减少 `--max-workers` 参数
- 检查网络连接
- 使用更快的模型（如 `--model gpt-3.5-turbo`）

## 扩展测试

### 添加更多漏洞

编辑 `test_project/app.py`，添加更多漏洞函数。例如：

```python
@app.route('/sqli')
def sqli():
    username = request.args.get('username')
    query = f"SELECT * FROM users WHERE username='{username}'"
    # 执行SQL查询...
```

### 测试其他攻击面

```bash
# 测试CLI应用
python main.py test_project python cli --skip-exploit

# 测试Protobuf应用
python main.py test_project python protobuf --skip-exploit
```

## 安全提醒

⚠️ **重要提示**:

1. 此测试应用仅用于教育和测试目的
2. 不要在生产环境中部署此应用
3. 不要将此应用暴露在公网上
4. 测试完成后及时停止应用
5. 确保你有权限审计目标代码

## 清理测试环境

```bash
# 停止测试应用（如果在运行）
# Ctrl+C

# 删除生成的报告
rm -rf code_audit_agent/reports/

# 删除生成的利用脚本
rm -rf code_audit_agent/tools/exploit_scripts/
rm -rf code_audit_agent/tools/screenshots/

# 删除生成的扫描脚本
rm -f code_audit_agent/scanners/generated_*.py
```

## 下一步

测试完成后，你可以：

1. 查看生成的报告，了解漏洞详情
2. 根据修复建议修复漏洞
3. 重新运行审计，验证修复效果
4. 将审计Agent应用到实际项目中

## 相关文件

- `README.md` - 主项目文档
- `ARCHITECTURE.md` - 架构说明
- `test_project/README.md` - 测试项目详细说明
- `run_test.py` - 自动化测试脚本
- `quick_test.sh` - 快速测试脚本
