import os
import json
import trace
import uuid
import traceback
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re

from rich.console import Console
from rich.syntax import Syntax

from ..utils.llm_response_parser import clean_and_parse
from ..utils.models import (
    FunctionInfo,
    TraceResult,
    CodeContext
)
from ..utils.llm_client import LLMClient
from ..utils.code_environment import CodeEnvironment
from ..utils.knowledge_base import KnowledgeBase

console = Console()


class TraceAgent:
    def __init__(self, llm_client: LLMClient, max_workers: int = 1, enable_lsp: bool = False, code_dir: str = None, project_type: Optional[str] = None, attack_surface: Optional[str] = None, docker_manager=None):
        self.llm_client = llm_client
        self.max_workers = max_workers
        self.enable_lsp = enable_lsp
        self.code_dir = code_dir
        self.knowledge_base = KnowledgeBase()
        self.project_type = project_type
        self.attack_surface = attack_surface
        self.docker_manager = docker_manager


    def trace_function(self, function_info: FunctionInfo) -> TraceResult:
        """使用 ACI 命令模式追踪函数数据流"""
        
        env = CodeEnvironment(self.code_dir, self.docker_manager)

        
        knowledge = self.knowledge_base.get_full_knowledge(
            self.project_type,
            self.attack_surface
        )
        
        system_prompt = self._build_system_prompt(knowledge, env)
        user_prompt = self._build_user_prompt(function_info)
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        observation = f"环境已初始化。请开始追踪函数的数据流。优先使用lsp命令。"
        
        console.print()
        console.print(f"[bold cyan]{'═' * 20} Trace Agent {'═' * 20}[/bold cyan]")
        console.print(f"[bold cyan]追踪任务[/bold cyan]")
        console.print(f"文件: [green]{function_info.file_path}[/green]")
        console.print(f"[cyan]{'─' * 60}[/cyan]")

        
        # console.print()
        # console.print(f"[bold red]{'═' * 20} System Prompt {'═' * 20}[/bold red]")
        # console.print(system_prompt)
        # console.print(f"[red]{'─' * 60}[/red]")
        
        # console.print()
        # console.print(f"[bold blue]{'═' * 20} User Prompt {'═' * 20}[/bold blue]")
        # console.print(user_prompt)
        # console.print(f"[blue]{'─' * 60}[/blue]")
        
        for step in range(30):
            
            try:
                response_content, think_content = self.llm_client.chat(
                    messages=messages,
                    temperature=0,
                )
                try:
                    json_response = clean_and_parse(response_content)
                except json.JSONDecodeError:
                    console.print(f"[bold red]Step {step} 解析 JSON 失败，进行下一轮请求看看还正常不[/bold red]")
                    continue
                
                messages.append({
                    "role": "assistant",
                    "content": think_content
                })
                
                messages.append({
                    "role": "assistant",
                    "content": response_content
                })
                
                result = env.execute(json_response.get("action", ""))
                observation = result.get("output", result.get("error", ""))
                
                console.print()
                console.print(f"[bold yellow]{'═' * 20} command output {'═' * 20}[/bold yellow]")
                console.print(observation)
                console.print(f"[yellow]{'─' * 60}[/yellow]")
                messages.append({
                    "role": "user",
                    "content": f"上一个命令的输出: {observation}"
                })
                
                if result.get("done"):
                    console.print("\n[bold green]✓ 任务完成[/bold green]")
                    break
                    
            except Exception as e:
                console.print(traceback.format_exc())
                console.print(f"\n[bold red]Step {step} 异常:[/bold red] {str(e)}")
                observation = f"执行失败: {str(e)}"
                break
        
        messages.append({
            "role": "user",
            "content": self._build_final_prompt()
        })
        
        
        
        try:
            response = self.llm_client.chat(
                messages=messages,
                temperature=0,
                # response_format={
                #     "type": "json_object"
                # }
            )
            
            structured_response = clean_and_parse(response)
            
            code_map = []
            for item in structured_response.get("code_map", []):
                code_map.append(CodeContext(
                    file_path=item["file_path"],
                    line_start=item["line_start"],
                    line_end=item["line_end"],
                    code_snippet=item["code_snippet"],
                    context_type=item.get("context_type", "function")
                ))
            
            return TraceResult(
                task_id=str(uuid.uuid4()),
                function_info=function_info,
                attack_surface=self.attack_surface,
                project_type=self.project_type,
                code_logic=structured_response.get("code_logic", ""),
                trace_complete=True,
                error_message=None,
                code_map=code_map,
                full_msg=json.dumps(messages, ensure_ascii=False, indent=2)
            )
        except Exception as e:
            # 打印详细的错误信息和调用栈
            console.print(f"[bold red]追踪任务失败: {str(e)}[/bold red]")
            console.print(f"[bold red]调用栈: {traceback.format_exc()}[/bold red]")
            return TraceResult(
                task_id=str(uuid.uuid4()),
                function_info=function_info,
                attack_surface=self.attack_surface,
                project_type=self.project_type,
                code_logic="",
                trace_complete=False,
                error_message=str(e)
            )


    def _build_system_prompt(self, knowledge: str, env: CodeEnvironment) -> str:
        tools_prompt = env.get_tools_prompt()
        
        prompt = f"""你是一个专业的代码安全分析专家，擅长追踪外部输入在代码中的数据流。

## 你的任务

1. 根据提供的外部输入源知识，识别接口函数中的外部输入
2. 追踪这些外部输入在代码中的传播路径
3. 找出所有被外部输入污染的函数调用
4. 使用 ACI 工具跳转到被调用函数，继续追踪
5. 递归追踪直到没有新的函数被污染

{tools_prompt}

## 外部输入源知识

{knowledge}

## ⚠️ 重要约束 - 追踪范围限制

**你必须严格遵守以下约束：**

1. **只追踪当前指定的入口函数**：你的追踪范围仅限于user prompt中提供的函数
2. **只追踪被污染的子函数**：只追踪入口函数调用的、且被外部输入污染的子函数
3. **不要追踪其他函数**：即使你在同一个文件中看到其他函数，也不要追踪它们
4. **不要使用open命令打开整个文件**：只使用go_to_def跳转到被调用的子函数
5. **不要使用search命令搜索其他函数**：只搜索入口函数内部使用的函数
6. **保持追踪的单一性**：每个追踪任务只分析一个入口函数及其被污染的子函数，不要混淆多个函数的结果

## 重要提示

1. 文件查看器每次只显示100行，使用行号范围查看特定部分
2. 每次只能执行一个命令
3. 等待命令执行结果后再进行下一步
4. 追踪完成后使用 submit 提交结果"""
        
        return prompt

    def _build_user_prompt(self, function_info: FunctionInfo) -> str:
        return f"""## 追踪任务

**攻击面**: {self.attack_surface}
**项目类型**: {self.project_type if self.project_type else 'c'}

## ⚠️ 重要提醒：只追踪入口函数及其被污染的子函数

**当前追踪的入口函数**: {function_info.function_name if function_info.function_name else '见下方代码'}

**你必须严格遵守以下规则：**
1. **只追踪下方代码片段中的入口函数**，不要追踪任何其他函数
2. **只追踪被污染的子函数**：只追踪入口函数调用的、且被外部输入污染的子函数
3. 即使你在文件中看到其他函数，也不要分析它们
4. 你的追踪结果应该只包含入口函数及其被污染的子函数
5. **不要追踪同级别的其他函数**：例如，如果追踪handle_index，不要追踪handle_ping、handle_read等其他handle函数

## 接口函数

**文件路径**: {function_info.file_path}

## 代码片段

```c
{function_info.code_snippet}
```

## 追踪要求

1. 识别代码中哪些变量接收了外部输入（参考外部输入源知识）
2. 追踪这些变量在入口函数内的传播路径
3. 找出所有被污染数据调用的函数（子函数）
4. 继续追踪被调用函数内部的数据流（只追踪被污染的路径）
5. 递归追踪直到没有新的函数被污染
6. 使用 submit 提交最终结果
7. 优先使用lsp工具获取准确定义和调用，次选文件打开和搜索

## 输出要求

你需要输出一个结构化的 JSON 对象，包含以下字段：

1. action (string): 执行的操作，例如 "go_to_def"、"search"、"view" 等
2. logic (string): 执行操作的详细逻辑描述，包括参数、调用顺序等

## 输出示例

```json
{{
    "action": "go_to_def main.c:11:handle_index",
    "logic": "外部输入是xx，xx作为参数传递给handle_index函数，跳转到handle_index函数定义"
}}
```

请开始追踪！"""

    def _build_final_prompt(self) -> str:
        return """请基于以上探索结果，输出最终的追踪报告。

## ⚠️ 关键要求：只输出入口函数及其被污染的子函数

**你必须严格遵守以下规则：**
1. **只包含入口函数及其被污染的子函数**：code_logic和code_map只应该包含入口函数以及被外部输入污染的子函数
2. **不要包含其他函数**：即使你在探索过程中看到了其他函数，也不要包含在结果中
3. **保持单一性**：每个追踪任务只对应一个入口函数及其被污染的子函数，不要混淆多个函数的结果
4. **验证你的结果**：在输出前，检查code_logic和code_map是否只包含入口函数及其被污染的子函数
5. **示例说明**：如果追踪handle_index，结果中应该只包含handle_index（如果没有外部输入污染）或handle_index及其被污染的子函数，不应该包含handle_ping、handle_read等其他handle函数

## 输出要求

你需要输出一个结构化的 JSON 对象，包含以下字段：

1. **code_logic** (string): 数据流追踪结果的详细描述，包括：
   - 入口函数信息（函数名、文件、行号）
   - 外部输入源和污染变量
   - 被污染函数的调用顺序（仅包含入口函数及其被污染的子函数）
   - 追踪过程总结

2. **code_map** (array): 被污染函数的代码上下文列表，每个元素包含：
   - file_path: 文件路径（字符串）
   - line_start: 起始行号（整数）
   - line_end: 结束行号（整数）
   - code_snippet: 完整的函数代码内容（字符串，带行号）
   - context_type: 上下文类型，固定为 "function"

## 重要提示

1. code_map 必须包含所有被污染的函数，包括入口函数
2. 按照调用顺序排列函数，入口函数放在第一个
3. 每个函数的 code_snippet 必须包含完整的代码内容，并标注行号
4. 确保所有字段都符合 JSON schema 的要求
5. 不要输出任何 JSON 格式之外的内容
6. **最重要：只包含入口函数及其被污染的子函数，不要包含任何其他函数**

## 输出示例

{
  "code_logic": "入口函数: handle_request (request_handler.c:10-50)\\n外部输入: HTTP请求 → request参数\\n被污染函数: handle_request → parse_input → process_data → execute_command\\n追踪过程: 从handle_request开始，request参数被传递到parse_input，解析后的数据传递给process_data，最终传递给execute_command执行命令。",
  "code_map": [
    {
      "file_path": "request_handler.c",
      "line_start": 10,
      "line_end": 50,
      "code_snippet": "10  int handle_request(char* request) {\\n11    char* input = parse_input(request);\\n12    process_data(input);\\n13    return 0;\\n14  }",
      "context_type": "function"
    },
    {
      "file_path": "parser.c",
      "line_start": 5,
      "line_end": 20,
      "code_snippet": "5  char* parse_input(char* input) {\\n6    char* result = malloc(256);\\n7    strcpy(result, input);\\n8    return result;\\n9  }",
      "context_type": "function"
    }
  ]
}

请按照上述格式输出结构化的 JSON 结果。"""

    def trace_functions_concurrent(self, function_infos: List[FunctionInfo]) -> List[TraceResult]:
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {executor.submit(self.trace_function, function_info): function_info for function_info in function_infos}
            
            for future in as_completed(future_to_task):
                function_info = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.trace_complete:
                        print(f"追踪完成: {function_info.file_path}:{function_info.function_name}")
                    else:
                        print(f"追踪失败: {function_info.file_path}:{function_info.function_name}")
                except Exception as e:
                    # 打印详细的错误信息和调用栈
                    console.print(f"[bold red]追踪任务 {function_info.function_name} 异常: {str(e)}[/bold red]")
                    console.print(f"[bold red]调用栈: {traceback.format_exc()}[/bold red]")
        
        return results

    def get_complete_traces_only(self, results: List[TraceResult]) -> List[TraceResult]:
        return [r for r in results if r.trace_complete]

    def save_trace_results(self, trace_results: List[TraceResult], filename: str = None) -> str:
        """
        保存追踪结果到JSON文件
        
        Args:
            trace_results: 追踪结果列表
            filename: 保存的文件名，如果不提供则自动生成
            
        Returns:
            保存的文件路径
        """
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trace_results_{timestamp}.json"
        
        report_path = os.path.join(reports_dir, filename)
        
        # 将TraceResult对象转换为可序列化的字典
        serializable_results = []
        for result in trace_results:
            serializable_result = {
                "task_id": result.task_id,
                "function_info": {
                    "file_path": result.function_info.file_path,
                    "function_name": result.function_info.function_name,
                    "code_snippet": result.function_info.code_snippet
                },
                "attack_surface": result.attack_surface,
                "project_type": result.project_type,
                "code_logic": result.code_logic,
                "trace_complete": result.trace_complete,
                "error_message": result.error_message,
                "full_msg": result.full_msg,
                "code_map": [
                    {
                        "file_path": ctx.file_path,
                        "line_start": ctx.line_start,
                        "line_end": ctx.line_end,
                        "code_snippet": ctx.code_snippet,
                        "context_type": ctx.context_type
                    }
                    for ctx in result.code_map
                ]
            }
            serializable_results.append(serializable_result)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]追踪结果已保存到: {report_path}[/green]")
        return report_path

    def load_trace_results(self, filepath: str) -> List[TraceResult]:
        """
        从JSON文件加载追踪结果
        
        Args:
            filepath: JSON文件路径
            
        Returns:
            追踪结果列表
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"追踪结果文件不存在: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            serializable_results = json.load(f)
        
        trace_results = []
        for serializable_result in serializable_results:
            # 重建FunctionInfo对象
            function_info = FunctionInfo(
                file_path=serializable_result["function_info"]["file_path"],
                function_name=serializable_result["function_info"]["function_name"],
                code_snippet=serializable_result["function_info"]["code_snippet"]
            )
            
            # 重建CodeContext对象列表
            code_map = []
            for ctx_dict in serializable_result["code_map"]:
                code_map.append(CodeContext(
                    file_path=ctx_dict["file_path"],
                    line_start=ctx_dict["line_start"],
                    line_end=ctx_dict["line_end"],
                    code_snippet=ctx_dict["code_snippet"],
                    context_type=ctx_dict["context_type"]
                ))
            
            # 重建TraceResult对象
            trace_result = TraceResult(
                task_id=serializable_result["task_id"],
                function_info=function_info,
                attack_surface=serializable_result["attack_surface"],
                project_type=serializable_result["project_type"],
                code_logic=serializable_result["code_logic"],
                trace_complete=serializable_result["trace_complete"],
                error_message=serializable_result["error_message"],
                full_msg=serializable_result["full_msg"],
                code_map=code_map
            )
            
            trace_results.append(trace_result)
        
        console.print(f"[green]已从文件加载 {len(trace_results)} 个追踪结果[/green]")
        return trace_results

    def generate_trace_report(self, trace_results: List[TraceResult]) -> str:
        """
        生成追踪结果的HTML报告
        
        Args:
            trace_results: 追踪结果列表
            
        Returns:
            报告文件路径
        """
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"trace_report_{timestamp}.html"
        report_path = os.path.join(reports_dir, report_filename)
        
        html_content = self._generate_trace_html(trace_results)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return report_path

    def _generate_trace_html(self, trace_results: List[TraceResult]) -> str:
        """
        生成追踪结果的HTML内容
        """
        complete_count = sum(1 for r in trace_results if r.trace_complete)
        failed_count = len(trace_results) - complete_count
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>数据流追踪报告</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6; 
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{ 
            max-width: 1400px; 
            margin: 0 auto; 
            background-color: white; 
            padding: 40px; 
            border-radius: 12px; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        .header {{ 
            text-align: center; 
            margin-bottom: 40px; 
            padding-bottom: 20px;
            border-bottom: 3px solid #667eea;
        }}
        .header h1 {{ 
            color: #667eea; 
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        .header .subtitle {{ 
            color: #666; 
            font-size: 1.1em;
        }}
        .summary {{ 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .summary-card {{ 
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card h3 {{ 
            font-size: 0.9em;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .summary-card .number {{ 
            font-size: 2.5em;
            font-weight: bold;
        }}
        .summary-card.success {{ background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); }}
        .summary-card.error {{ background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%); }}
        .summary-card.info {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        
        .trace-item {{ 
            border: 1px solid #e0e0e0; 
            border-radius: 8px; 
            margin-bottom: 20px; 
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        .trace-item:hover {{ 
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        .trace-item.completed {{ border-left: 5px solid #4CAF50; }}
        .trace-item.failed {{ border-left: 5px solid #f44336; }}
        
        .trace-header {{ 
            background-color: #f5f5f5; 
            padding: 20px; 
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: background-color 0.3s ease;
        }}
        .trace-header:hover {{ 
            background-color: #e8e8e8;
        }}
        .trace-header-info {{ flex: 1; }}
        .trace-header h3 {{ 
            color: #333; 
            margin-bottom: 5px;
            font-size: 1.2em;
        }}
        .trace-header .meta {{ 
            color: #666; 
            font-size: 0.9em;
        }}
        .trace-header .status {{ 
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            margin-left: 20px;
        }}
        .status.completed {{ 
            background-color: #4CAF50; 
            color: white;
        }}
        .status.failed {{ 
            background-color: #f44336; 
            color: white;
        }}
        .expand-icon {{ 
            font-size: 1.5em;
            color: #667eea;
            transition: transform 0.3s ease;
            margin-left: 20px;
        }}
        .trace-item.expanded .expand-icon {{ 
            transform: rotate(180deg);
        }}
        
        .trace-content {{ 
            display: none; 
            padding: 20px;
            background-color: #fafafa;
        }}
        .trace-item.expanded .trace-content {{ 
            display: block;
        }}
        
        .info-grid {{ 
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .info-item {{ 
            background-color: white;
            padding: 15px;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .info-item .label {{ 
            color: #667eea;
            font-weight: bold;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}
        .info-item .value {{ 
            color: #333;
            word-break: break-all;
        }}
        
        .section {{ 
            margin-bottom: 25px;
        }}
        .section h4 {{ 
            color: #667eea;
            margin-bottom: 15px;
            padding-bottom: 8px;
            border-bottom: 2px solid #667eea;
            font-size: 1.1em;
        }}
        
        pre {{ 
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 0.9em;
            line-height: 1.5;
        }}
        code {{ 
            background-color: #f0f0f0;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        
        .code-map-table {{ 
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .code-map-table th {{ 
            background-color: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: bold;
        }}
        .code-map-table td {{ 
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}
        .code-map-table tr:hover {{ 
            background-color: #f5f5f5;
        }}
        
        .error-message {{ 
            background-color: #ffebee;
            color: #c62828;
            padding: 15px;
            border-radius: 6px;
            border-left: 4px solid #f44336;
            margin-top: 15px;
        }}
        
        .empty-state {{ 
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }}
        .empty-state .icon {{ 
            font-size: 4em;
            margin-bottom: 20px;
        }}
        
        @media (max-width: 768px) {{
            .container {{ padding: 20px; }}
            .header h1 {{ font-size: 1.8em; }}
            .summary {{ grid-template-columns: 1fr; }}
            .trace-header {{ flex-direction: column; align-items: flex-start; }}
            .trace-header .status {{ margin-left: 0; margin-top: 10px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 数据流追踪报告</h1>
            <div class="subtitle">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card info">
                <h3>总追踪任务</h3>
                <div class="number">{len(trace_results)}</div>
            </div>
            <div class="summary-card success">
                <h3>成功追踪</h3>
                <div class="number">{complete_count}</div>
            </div>
            <div class="summary-card error">
                <h3>失败追踪</h3>
                <div class="number">{failed_count}</div>
            </div>
        </div>
"""
        
        if not trace_results:
            html += """
        <div class="empty-state">
            <div class="icon">📭</div>
            <h3>暂无追踪结果</h3>
            <p>没有找到任何追踪任务数据</p>
        </div>
"""
        else:
            for i, trace_result in enumerate(trace_results, 1):
                status_class = "completed" if trace_result.trace_complete else "failed"
                status_text = "✓ 成功" if trace_result.trace_complete else "✗ 失败"
                
                html += f"""
        <div class="trace-item {status_class}" data-id="{i}">
            <div class="trace-header" onclick="toggleTrace({i})">
                <div class="trace-header-info">
                    <h3>{i}. {trace_result.function_info.function_name}</h3>
                    <div class="meta">
                        <span>📁 {trace_result.function_info.file_path}</span>
                    </div>
                </div>
                <div class="status {status_class}">{status_text}</div>
                <div class="expand-icon">▼</div>
            </div>
            
            <div class="trace-content" id="trace-content-{i}">
                <div class="info-grid">
                    <div class="info-item">
                        <div class="label">任务ID</div>
                        <div class="value">{trace_result.task_id}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">项目类型</div>
                        <div class="value">{trace_result.project_type}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">攻击面</div>
                        <div class="value">{trace_result.attack_surface}</div>
                    </div>
                    <div class="info-item">
                        <div class="label">追踪状态</div>
                        <div class="value">{status_text}</div>
                    </div>
                </div>
"""
                
                if trace_result.error_message:
                    html += f"""
                <div class="error-message">
                    <strong>❌ 错误信息:</strong><br>
                    {trace_result.error_message}
                </div>
"""
                
                html += """
                <div class="section">
                    <h4>📝 代码逻辑</h4>
                    <pre>""" + self._escape_html(trace_result.code_logic) + """</pre>
                </div>
"""
                
                if trace_result.code_map:
                    html += """
                <div class="section">
                    <h4>🗺️ 代码地图</h4>
                    <table class="code-map-table">
                        <thead>
                            <tr>
                                <th>序号</th>
                                <th>文件路径</th>
                                <th>行号</th>
                                <th>上下文类型</th>
                            </tr>
                        </thead>
                        <tbody>
"""
                    for j, code_context in enumerate(trace_result.code_map, 1):
                        html += f"""
                            <tr>
                                <td>{j}</td>
                                <td><code>{code_context.file_path}</code></td>
                                <td>{code_context.line_start}-{code_context.line_end}</td>
                                <td>{code_context.context_type}</td>
                            </tr>
"""
                    html += """
                        </tbody>
                    </table>
                </div>
"""
                
                if trace_result.full_msg:
                    html += """
                <div class="section">
                    <h4>💬 LLM对话记录</h4>
                    <pre>""" + self._escape_html(trace_result.full_msg) + """</pre>
                </div>
"""
                
                html += """
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <script>
        function toggleTrace(id) {
            const item = document.querySelector(`.trace-item[data-id="${id}"]`);
            item.classList.toggle('expanded');
        }
        
        // 默认展开第一个追踪结果
        document.addEventListener('DOMContentLoaded', function() {
            const firstTrace = document.querySelector('.trace-item');
            if (firstTrace) {
                firstTrace.classList.add('expanded');
            }
        });
    </script>
</body>
</html>
"""
        return html

    def _escape_html(self, text: str) -> str:
        """
        转义HTML特殊字符
        """
        if not text:
            return ""
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#039;')
        return text
