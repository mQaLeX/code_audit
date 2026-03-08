# 代码审计AI Agent

基于LLM的代码审计+自动化利用+自动生成报告的AI Agent系统。

## 功能特性

- 多Agent架构，支持并发审计
- 支持多种项目类型（Python、Java、Go、JavaScript、C），基于 knowledge 目录动态加载
- 支持多种攻击面（Web、CLI、Protobuf、Blink），基于 knowledge 目录动态加载
- 列表查询功能，快速查看支持的类型和漏洞
- 自动扫描接口函数
- 智能代码审计
- 自动化漏洞利用
- 生成多种格式的安全报告（Markdown、JSON、HTML）
- 不使用LangChain，直接调用OpenAI API

## 项目结构

```
code_audit/
├── code_audit_agent/
│   ├── agents/              # Agent模块
│   │   ├── audit_agent.py   # 代码审计Agent
│   │   ├── exploit_agent.py # 漏洞利用Agent
│   │   └── report_agent.py  # 报告生成Agent
│   ├── scanners/            # 扫描模块
│   │   ├── function_scanner.py
│   │   ├── scan_python_web.py
│   │   └── scan_python_cli.py
│   ├── knowledge/           # 知识库
│   │   ├── python/
│   │   │   ├── web/
│   │   │   │   ├── SQL注入.txt
│   │   │   │   ├── XSS攻击.txt
│   │   │   │   └── ...
│   │   │   ├── cli/
│   │   │   │   ├── 命令注入.txt
│   │   │   │   └── ...
│   │   │   ├── protobuf/
│   │   │   └── blink/
│   │   ├── c/
│   │   │   └── web/
│   │   ├── java/
│   │   ├── go/
│   │   └── javascript/
│   ├── tools/               # 工具目录
│   │   ├── exploit_scripts/
│   │   └── screenshots/
│   ├── reports/             # 报告输出目录
│   └── utils/               # 工具模块
│       ├── llm_client.py
│       └── models.py
├── main.py                  # 主程序入口
├── requirements.txt         # 依赖文件
└── .env.example            # 环境变量示例
```

## 安装

1. 克隆项目：
```bash
git clone <repository_url>
cd code_audit
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置环境变量：
```bash
cp .env.example .env
```

编辑`.env`文件，设置你的OpenAI API密钥：
```
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 使用方法

### 基础用法

```bash
# 审计Python Web应用
python main.py python web /path/to/code

# 审计C语言civetweb应用
python main.py c civetweb /path/to/code
```

### 列表查询

```bash
python main.py list                           # 查看支持的project_type
python main.py <project_type> list            # 查看指定project_type支持的attack_surface
python main.py <project_type> <attack_surface> list  # 查看支持的漏洞类型
```

### 会话管理

```bash
python main.py --list sessions               # 列出所有历史会话
python main.py --session <会话ID>             # 恢复历史会话
python main.py --session <会话ID> --from-stage audit  # 从审计阶段继续
```

### 历史结果使用

```bash
python main.py --list trace                  # 列出历史追踪结果
python main.py --trace <文件名>               # 使用历史追踪结果继续
python main.py --list audit                  # 列出历史审计结果
python main.py --audit <文件名>               # 使用历史审计结果进行漏洞利用
python main.py --list exploit                # 列出历史利用结果
python main.py --exploit <文件名>             # 使用历史利用结果生成报告
```

### 常用选项

```bash
python main.py <project_type> <attack_surface> <code_dir> --verbose    # 显示详细输出
python main.py <project_type> <attack_surface> <code_dir> --debug      # 显示LLM交互消息
python main.py <project_type> <attack_surface> <code_dir> --model gpt-4o  # 指定模型
python main.py <project_type> <attack_surface> <code_dir> --max-workers 5  # 并发数
python main.py <project_type> <attack_surface> <code_dir> --skip-exploit  # 跳过漏洞利用
```

### LSP用法（C项目）

```bash
python main.py c civetweb /path/to/code --enable-lsp                    # 启用LSP
python main.py c civetweb /path/to/code --enable-lsp --lsp-command clangd-17  # 指定LSP版本
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `project_type` | 项目类型 | python/c/go |
| `attack_surface` | 攻击面 | web/cli/protobuf/blink/civetweb |
| `code_dir` | 代码目录路径 | - |

### 可选参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--api-key` | OpenAI API密钥 | 环境变量 OPENAI_API_KEY |
| `--base-url` | OpenAI API基础URL | 环境变量 OPENAI_BASE_URL |
| `--model` | 使用的LLM模型 | gpt-4o |
| `--max-workers` | 并发审计的最大工作线程数 | 1 |
| `--output-dir` | 报告输出目录 | ./reports |
| `--skip-exploit` | 跳过漏洞利用步骤 | False |
| `--report-format` | 报告格式（markdown/json/html/all） | markdown |
| `--verbose` | 显示详细输出 | False |
| `--debug` | 显示LLM客户端交互的消息内容 | False |
| `--enable-lsp` | 启用LSP（clangd）工具调用 | False |
| `--lsp-command` | LSP服务器命令 | clangd |
| `--list` | 列出历史: sessions/trace/audit/exploit | - |
| `--session` | 指定会话ID恢复历史会话 | - |
| `--from-stage` | 从指定阶段开始: scanner/trace/audit/exploit/report | - |
| `--trace` | 使用历史追踪结果 | - |
| `--audit` | 使用历史审计结果 | - |
| `--exploit` | 使用历史漏洞利用结果 | - |

### 使用示例

#### 列表查询

查看支持的项目类型：
```bash
python main.py list
```

查看Python支持的攻击面：
```bash
python main.py python list
```

查看Python CLI支持的漏洞类型：
```bash
python main.py python cli list
```

#### 代码审计

审计Python Web应用：
```bash
python main.py python web /path/to/code
```

审计Python CLI应用：
```bash
python main.py python cli /path/to/code
```

审计Python Protobuf应用：
```bash
python main.py python protobuf /path/to/code
```

审计Python Blink应用：
```bash
python main.py python blink /path/to/code
```

审计C语言Web应用（civetweb）：
```bash
python main.py c civetweb /path/to/code
```

启用LSP（需要 compile_commands.json）：
```bash
python main.py c civetweb /path/to/code --enable-lsp
```

恢复历史会话：
```bash
python main.py --session <会话ID>
```

使用自定义模型和并发数：
```bash
python main.py python web /path/to/code --model gpt-4 --max-workers 10
```

只生成JSON报告：
```bash
python main.py python web /path/to/code --report-format json
```

跳过漏洞利用：
```bash
python main.py python web /path/to/code --skip-exploit
```

## 工作流程

1. **扫描接口函数**
   - 根据项目类型和攻击面加载对应的扫描脚本或知识库
   - 如果是扫描脚本，直接调用扫描
   - 如果是知识库，调用LLM生成扫描脚本，然后使用ast-grep解析代码

2. **创建审计任务**
   - 对每个接口函数，根据攻击面预设的问题类型创建审计任务
   - 生成 n（函数数量）* m（问题类型）个审计任务

3. **并发审计**
   - 使用线程池并发执行审计任务
   - 每个任务调用LLM进行代码审计
   - 返回审计结果，包括是否存在漏洞、漏洞类型、严重程度等

4. **漏洞利用**
   - 对确认存在漏洞的函数，调用漏洞利用Agent
   - 生成利用脚本并执行
   - 判断利用是否成功
   - 可选截图保存

5. **生成报告**
   - 汇总审计结果和利用结果
   - 生成包含以下内容的报告：
     - 漏洞类型
     - 漏洞路径（文件目录相对路径）
     - 漏洞详情
     - 漏洞利用截图/脚本
     - 漏洞影响
     - CVSS评分

## 扩展知识库

### 添加新的扫描脚本

在`code_audit_agent/scanners/`目录下创建新的扫描脚本，命名格式为`scan_<project_type>_<attack_surface>.py`。

脚本需要实现一个`scan(code_dir: str) -> list`函数，返回包含函数信息的列表。

### 添加新的漏洞类型

在`code_audit_agent/knowledge/<project_type>/<attack_surface>/`目录下创建新的漏洞类型文件，命名格式为`<漏洞类型>.txt`。

漏洞类型文件格式：
```
漏洞类型名称
漏洞描述和审计问题...
```

例如，添加一个新的漏洞类型：
```
文件包含漏洞
检查代码中是否存在文件包含漏洞，特别是用户可控的文件路径...
```

### 添加新的项目类型或攻击面

1. 在`code_audit_agent/knowledge/`目录下创建新的项目类型目录（如`java/`）
2. 在项目类型目录下创建攻击面子目录（如`web/`）
3. 在攻击面子目录下添加漏洞类型文件（如`SQL注入.txt`）

**注意**：添加新的项目类型或攻击面后，无需修改代码，系统会自动识别并支持新的类型。使用 `python main.py list` 可以查看当前支持的所有项目类型和攻击面。

## 注意事项

1. 本工具仅用于授权的安全测试
2. 使用前请确保你有权限审计目标代码
3. 漏洞利用功能应在受控环境中使用
4. 建议使用`--skip-exploit`参数先进行审计，确认后再进行利用
5. 请妥善保管API密钥，不要提交到版本控制系统

## 许可证

MIT License
