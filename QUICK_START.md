# 快速启动指南

## 安装步骤

```bash
# 1. 克隆项目
cd /Users/lometsj/Documents/llm_tool/code_audit

# 2. 安装依赖
pip install -r requirements.txt

# 3. 配置环境变量
cp .env.example .env
# 编辑.env文件，设置你的OpenAI API密钥
```

## 启动TUI应用

```bash
# 方式1：使用TUI入口
python tui_main.py

# 方式2：直接运行模块
python -m code_audit_agent.tui.app
```

## 启动CLI应用（保留原有功能）

```bash
# 方式1：使用CLI入口
python cli_main.py python web /path/to/code

# 方式2：使用原有的main.py
python main.py python web /path/to/code
```

## 功能说明

### TUI应用功能

1. **主界面**
   - 输入代码目录路径或点击"浏览"按钮选择
   - 选择项目类型和攻击面（多选）
   - 点击"确定"开始审计

2. **审计界面**
   - 查看Agent执行流程（scanner→trace_agent→audit_agent→exploit_agent→report_agent）
   - 实时查看LLM对话内容
   - 支持鼠标滚动查看历史消息
   - 消息可折叠/展开
   - 可选择启用"干扰模式"，在LLM调用时暂停等待用户输入

3. **鼠标交互**
   - 点击选择项目类型和攻击面
   - 滚轮滚动查看内容
   - 点击消息可展开/收起

### CLI应用功能

保留原有的命令行功能，支持所有审计功能：

```bash
# 列出支持的项目类型
python main.py list

# 列出指定项目类型支持的攻击面
python main.py python list

# 列出指定项目类型和攻击面支持的漏洞类型
python main.py python web list

# 开始审计
python main.py python web /path/to/code

# 使用自定义参数
python main.py python web /path/to/code --model gpt-4 --max-workers 10

# 跳过漏洞利用
python main.py python web /path/to/code --skip-exploit

# 生成JSON报告
python main.py python web /path/to/code --report-format json
```

## 界面截图说明

### 主界面
```
┌─────────────────────────────────────────────────────────────┐
│  代码目录输入框                                              │
│  [________________输入代码目录路径______________] [浏览]     │
├─────────────────────────────────────────────────────────────┤
│  选择项目类型和攻击面（可多选）:                             │
│  □ c                                                        │
│  □   civetweb                                               │
│  □ python                                                   │
│  □   cli                                                    │
├─────────────────────────────────────────────────────────────┤
│  [确定] [重置]                                              │
└─────────────────────────────────────────────────────────────┘
```

### 审计界面
```
┌─────────────────────────────────────────────────────────────┐
│  代码审计AI Agent - 审计中                                   │
├─────────────────────────────────────────────────────────────┤
│  Agent流程: scanner ➜ trace_agent ➜ audit_agent ➜        │
│             exploit_agent ➜ report_agent                   │
│             (当前进行中)                                     │
├─────────────────────────────────────────────────────────────┤
│  LLM对话                                                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 👤 用户消息                                           │  │
│  │ [展开/收起]                                           │  │
│  │ ...                                                   │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🤖 AI响应                                             │  │
│  │ [展开/收起]                                           │  │
│  │ ...                                                   │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  [输入消息...] [干扰模式□] [发送]                           │
└─────────────────────────────────────────────────────────────┘
```

## 注意事项

1. **终端要求**：建议使用支持鼠标事件的现代终端
   - macOS: iTerm2、Terminal
   - Windows: Windows Terminal
   - Linux: GNOME Terminal、Konsole

2. **API配置**：确保已正确配置OpenAI API密钥
   ```bash
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_BASE_URL="https://api.openai.com/v1"
   ```

3. **性能优化**：建议设置合理的并发数
   ```bash
   python main.py python web /path/to/code --max-workers 5
   ```

## 故障排除

### 问题1：TUI无法启动
**解决方案**：
- 确保已安装Textual：`pip install textual>=0.40.0`
- 检查Python版本：`python --version`（需要3.8+）
- 查看错误信息：`python tui_main.py`（会显示详细错误）

### 问题2：鼠标事件不工作
**解决方案**：
- 确保终端支持鼠标事件
- 在iTerm2中：Preferences → Profiles → Terminal → Enable mouse reporting
- 在Windows Terminal中：通常默认启用

### 问题3：LLM调用失败
**解决方案**：
- 检查API密钥是否正确
- 检查网络连接
- 查看错误信息：`python main.py --debug`

## 下一步

1. 阅读[TUI_README.md](TUI_README.md)了解更多信息
2. 阅读[TUI_GUIDE.md](TUI_GUIDE.md)了解详细使用指南
3. 运行测试：`python test_tui_complete.py`
