#!/usr/bin/env python3
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from code_audit_agent.agents.trace_agent import TraceAgent
from code_audit_agent.utils.llm_client import LLMClient
from code_audit_agent.utils.models import FunctionInfo

console = Console()


def test_trace_agent():
    llm_client = LLMClient()
    llm_client.debug = True
    code_dir = "/Users/lometsj/Documents/llm_tool/code_audit/test_cproject"

    trace_agent = TraceAgent(
        llm_client=llm_client,
        max_workers=1,
        enable_lsp=True,
        code_dir=code_dir,
    )
    start_line = 28
    end_line = 75
    #代码片段加上行号
    with open(os.path.join(code_dir, "main.c"), 'r', encoding='utf-8') as f:
                lines = f.readlines()
                code_snippet = ''.join(f"{i+start_line:6d} | {line}" for i, line in enumerate(lines[start_line-1:end_line]))
            
    function_info = FunctionInfo(
        file_path="main.c",
        function_name="handle_ping",
        line_number=280,
    )
    
    task = trace_agent.create_trace_tasks(
        functions=[function_info],
        attack_surface="civetweb",
        project_type="c"
    )[0]
    
    console.print(Panel.fit(
        f"[bold]Task ID:[/bold] {task.task_id}\n"
        f"[bold]函数:[/bold] [yellow]{task.function_info.function_name}[/yellow]\n"
        f"[bold]文件:[/bold] [green]{task.function_info.file_path}[/green]\n"
        f"[bold]行号:[/bold] {task.function_info.line_start}-{task.function_info.line_end}",
        title="[bold cyan]开始追踪任务[/bold cyan]",
        border_style="cyan"
    ))
    
    result = trace_agent.trace_function(task)
    
    
    if result.data_flow_summary:
        console.print("\n")
        console.print(Panel(
            result.data_flow_summary,
            title="[bold cyan]数据流摘要[/bold cyan]",
            border_style="blue"
        ))
    
    
    if result.error_message:
        console.print(f"\n[bold red]错误:[/bold red] {result.error_message}")


if __name__ == "__main__":
    test_trace_agent()
