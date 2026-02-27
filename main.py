#!/usr/bin/env python3
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from code_audit_agent.utils import LLMClient
from code_audit_agent.scanners import FunctionScanner
from code_audit_agent.agents import AuditAgent, ExploitAgent, ReportAgent, TraceAgent

console = Console()


def get_knowledge_base_dir():
    """
    获取知识库目录路径
    """
    return os.path.join(os.path.dirname(__file__), 'code_audit_agent', 'knowledge')


def get_project_types():
    """
    获取所有支持的项目类型（从knowledge目录读取）
    """
    knowledge_dir = get_knowledge_base_dir()
    project_types = []
    
    if os.path.exists(knowledge_dir):
        for item in os.listdir(knowledge_dir):
            if os.path.isdir(os.path.join(knowledge_dir, item)):
                project_types.append(item)
    
    return sorted(project_types)


def get_attack_surfaces(project_type: str):
    """
    获取指定项目类型支持的攻击面（从knowledge目录读取）
    """
    knowledge_dir = get_knowledge_base_dir()
    project_dir = os.path.join(knowledge_dir, project_type)
    
    attack_surfaces = []
    
    if os.path.exists(project_dir):
        for item in os.listdir(project_dir):
            if os.path.isdir(os.path.join(project_dir, item)):
                attack_surfaces.append(item)
    
    return sorted(attack_surfaces)


def get_vulnerability_types(project_type: str, attack_surface: str):
    """
    获取指定项目类型和攻击面支持的漏洞类型（从knowledge目录读取）
    """
    knowledge_dir = get_knowledge_base_dir()
    vuln_dir = os.path.join(knowledge_dir, project_type, attack_surface)
    
    vuln_types = []
    
    if os.path.exists(vuln_dir):
        for item in os.listdir(vuln_dir):
            if item.endswith('.txt'):
                vuln_types.append(item[:-4])
    
    return sorted(vuln_types)


def parse_arguments():
    """
    解析命令行参数
    """
    project_types = get_project_types()
    all_attack_surfaces = set()
    for pt in project_types:
        all_attack_surfaces.update(get_attack_surfaces(pt))
    all_attack_surfaces = sorted(all_attack_surfaces)
    
    parser = argparse.ArgumentParser(
        description='基于LLM的代码审计AI Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
示例用法:
  python main.py python web /path/to/code
  python main.py python cli /path/to/code
  python main.py python protobuf /path/to/code
  python main.py python blink /path/to/code

列表查询:
  python main.py list                           # 查看支持的project_type
  python main.py <project_type> list            # 查看指定project_type支持的attack_surface
  python main.py <project_type> <attack_surface> list  # 查看支持的漏洞类型

支持的项目类型: {', '.join(project_types)}
支持的攻击面: {', '.join(all_attack_surfaces)}
        """
    )
    
    parser.add_argument(
        'project_type',
        nargs='?',
        choices=project_types + ['list'],
        help=f'项目类型（可选: {", ".join(project_types)}）'
    )
    
    parser.add_argument(
        'attack_surface',
        nargs='?',
        choices=all_attack_surfaces + ['list'],
        help=f'攻击面类型（可选: {", ".join(all_attack_surfaces)}）'
    )
    
    parser.add_argument(
        'list_type',
        nargs='?',
        help='列表查询（用于查看漏洞类型，使用 "list" 查看漏洞类型列表）'
    )
    
    parser.add_argument(
        'code_dir',
        nargs='?',
        help='要审计的代码目录路径'
    )
    
    parser.add_argument(
        '--api-key',
        help='OpenAI API密钥（如果不提供，将从环境变量OPENAI_API_KEY读取）'
    )
    
    parser.add_argument(
        '--base-url',
        help='OpenAI API基础URL（如果不提供，将从环境变量OPENAI_BASE_URL读取）'
    )
    
    parser.add_argument(
        '--model',
        help='使用的LLM模型（如果不提供，将从环境变量DEFAULT_MODEL读取）'
    )
    
    parser.add_argument(
        '--max-workers',
        type=int,
        default=1,
        help='并发审计的最大工作线程数（默认: 1）'
    )
    
    parser.add_argument(
        '--output-dir',
        help='报告输出目录（默认: ./reports）'
    )
    
    parser.add_argument(
        '--skip-exploit',
        action='store_true',
        help='跳过漏洞利用步骤，只进行审计'
    )
    
    parser.add_argument(
        '--report-format',
        choices=['markdown', 'json', 'html', 'all'],
        default='all',
        help='报告格式（默认: all）'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='显示详细输出'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='显示LLM客户端交互的消息内容'
    )
    
    parser.add_argument(
        '--enable-lsp',
        action='store_true',
        help='启用LSP（clangd）工具调用获取更多代码上下文'
    )
    
    parser.add_argument(
        '--lsp-command',
        nargs='+',
        default=['clangd'],
        help='LSP服务器命令（默认: clangd）'
    )
    
    parser.add_argument(
        '--trace',
        help='使用历史追踪结果："list"显示历史记录，或指定文件名直接使用该追踪结果'
    )
    
    return parser.parse_args()


def validate_code_directory(code_dir: str) -> bool:
    """
    验证代码目录是否存在
    """
    if not os.path.exists(code_dir):
        console.print(f"[bold red]错误: 代码目录不存在: {code_dir}[/bold red]")
        return False
    
    if not os.path.isdir(code_dir):
        console.print(f"[bold red]错误: 路径不是目录: {code_dir}[/bold red]")
        return False
    
    return True


def list_project_types():
    """
    列出支持的项目类型
    """
    project_types = get_project_types()
    
    table = Table(title="支持的项目类型 (Project Types)", box=box.ROUNDED)
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("项目类型", style="green")
    
    for i, pt in enumerate(project_types, 1):
        table.add_row(str(i), pt)
    
    console.print(table)


def list_attack_surfaces(project_type: str):
    """
    列出指定项目类型支持的攻击面
    """
    attack_surfaces = get_attack_surfaces(project_type)
    
    if attack_surfaces:
        table = Table(title=f"{project_type.upper()} 支持的攻击面 (Attack Surfaces)", box=box.ROUNDED)
        table.add_column("序号", style="cyan", justify="right")
        table.add_column("攻击面", style="green")
        
        for i, as_type in enumerate(attack_surfaces, 1):
            table.add_row(str(i), as_type)
        
        console.print(table)
    else:
        console.print(f"[yellow]暂无 {project_type} 的攻击面配置[/yellow]")


def list_vulnerability_types(project_type: str, attack_surface: str):
    """
    列出指定项目类型和攻击面支持的漏洞类型
    """
    vuln_types = get_vulnerability_types(project_type, attack_surface)
    
    if vuln_types:
        table = Table(title=f"{project_type.upper()} {attack_surface.upper()} 支持的漏洞类型 (Vulnerability Types)", box=box.ROUNDED)
        table.add_column("序号", style="cyan", justify="right")
        table.add_column("漏洞类型", style="green")
        
        for i, vuln_type in enumerate(vuln_types, 1):
            table.add_row(str(i), vuln_type)
        
        console.print(table)
    else:
        console.print(f"[yellow]暂无 {project_type} {attack_surface} 的漏洞类型配置[/yellow]")


def list_trace_results():
    """
    列出报告目录中的追踪结果文件
    """
    reports_dir = os.path.join(os.path.dirname(__file__), 'code_audit_agent', 'reports')
    
    if not os.path.exists(reports_dir):
        console.print("[yellow]报告目录不存在，暂无追踪结果[/yellow]")
        return
    
    trace_files = []
    for filename in os.listdir(reports_dir):
        if filename.startswith('trace_results_') and filename.endswith('.json'):
            file_path = os.path.join(reports_dir, filename)
            file_stat = os.stat(file_path)
            trace_files.append({
                'filename': filename,
                'filepath': file_path,
                'size': file_stat.st_size,
                'modified': datetime.fromtimestamp(file_stat.st_mtime)
            })
    
    if not trace_files:
        console.print("[yellow]暂无追踪结果文件[/yellow]")
        return
    
    # 按修改时间排序
    trace_files.sort(key=lambda x: x['modified'], reverse=True)
    
    table = Table(title="历史追踪结果文件", box=box.ROUNDED)
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("文件名", style="green")
    table.add_column("大小", style="yellow")
    table.add_column("修改时间", style="blue")
    
    for i, trace_file in enumerate(trace_files, 1):
        table.add_row(
            str(i),
            trace_file['filename'],
            f"{trace_file['size']} bytes",
            trace_file['modified'].strftime('%Y-%m-%d %H:%M:%S')
        )
    
    console.print(table)
    console.print("\n[bold]使用方法:[/bold]")
    console.print("  python main.py <project_type> <attack_surface> <code_dir> --trace <文件名>")
    console.print("  例如: python main.py c civetweb /path/to/code --trace trace_results_20260226_154943.json")


def main():
    """
    主函数
    """
    args = parse_arguments()
    
    # 处理 --trace list 选项（独立功能）
    if args.trace and args.trace.lower() == 'list':
        list_trace_results()
        sys.exit(0)
    
    if args.project_type == 'list':
        list_project_types()
        sys.exit(0)
    
    if args.attack_surface == 'list':
        list_attack_surfaces(args.project_type)
        sys.exit(0)
    
    if args.list_type == 'list':
        list_vulnerability_types(args.project_type, args.attack_surface)
        sys.exit(0)
    
    code_dir = args.code_dir if args.code_dir else args.list_type
    
    if not code_dir:
        console.print("[bold red]错误: 请提供代码目录路径[/bold red]")
        console.print("使用方法: python main.py <project_type> <attack_surface> <code_dir>")
        console.print("使用 'python main.py list' 查看支持的类型")
        sys.exit(1)
    
    if not validate_code_directory(code_dir):
        sys.exit(1)
    
    panel = Panel(
        f"""[cyan]代码目录:[/cyan] {code_dir}
[cyan]项目类型:[/cyan] {args.project_type}
[cyan]攻击面:[/cyan] {args.attack_surface}
[cyan]LLM模型:[/cyan] {args.model}
[cyan]并发线程数:[/cyan] {args.max_workers}
[cyan]跳过漏洞利用:[/cyan] {args.skip_exploit}
[cyan]报告格式:[/cyan] {args.report_format}
[cyan]调试模式:[/cyan] {args.debug}""",
        title="[bold blue]代码审计AI Agent[/bold blue]",
        border_style="blue",
        padding=(1, 2)
    )
    console.print(panel)
    console.print()
    
    try:
        llm_client = LLMClient(
            api_key=args.api_key,
            base_url=args.base_url,
            model=args.model,
            debug=args.debug
        )
        console.print("[green]✓ LLM客户端初始化成功[/green]")
    except Exception as e:
        console.print(f"[bold red]错误: LLM客户端初始化失败: {str(e)}[/bold red]")
        sys.exit(1)
    
    console.print()
    console.print(Panel("[bold yellow]步骤 1: 扫描接口函数...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
    
    try:
        scanner = FunctionScanner()
        project_type = args.project_type
        attack_surface = args.attack_surface
        
        functions = scanner.scan_functions(code_dir, project_type, attack_surface)
        
        console.print(f"[green]扫描完成，发现 {len(functions)} 个接口函数[/green]")
        
        if args.verbose:
            table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
            table.add_column("序号", style="cyan", width=6)
            table.add_column("文件路径", style="blue")
            table.add_column("函数名", style="green")
            table.add_column("行号", style="yellow")
            
            for i, func in enumerate(functions, 1):
                table.add_row(str(i), func.file_path, func.function_name, f"{func.line_start}-{func.line_end}")
            
            console.print(table)
    except Exception as e:
        console.print(f"[bold red]错误: 函数扫描失败: {str(e)}[/bold red]")
        sys.exit(1)
    
    if not functions:
        console.print("[yellow]未发现任何接口函数，审计结束[/yellow]")
        sys.exit(0)
    
    # 处理 --trace 选项（使用指定文件）
    if args.trace:
            # 使用指定的追踪结果文件
            reports_dir = os.path.join(os.path.dirname(__file__), 'code_audit_agent', 'reports')
            trace_file_path = os.path.join(reports_dir, args.trace)
            
            if not os.path.exists(trace_file_path):
                console.print(f"[bold red]错误: 追踪结果文件不存在: {trace_file_path}[/bold red]")
                sys.exit(1)
            
            try:
                trace_agent = TraceAgent(
                    llm_client=llm_client,
                    max_workers=args.max_workers,
                    enable_lsp=args.enable_lsp,
                    project_type=project_type,
                    attack_surface=attack_surface,
                    code_dir=code_dir
                )
                
                console.print(f"[bold yellow]步骤 2: 从文件加载追踪结果...[/bold yellow]")
                trace_results = trace_agent.load_trace_results(trace_file_path)
                complete_traces = trace_agent.get_complete_traces_only(trace_results)
                
                console.print(f"[green]✓ 已从文件加载 {len(trace_results)} 个追踪结果，其中 {len(complete_traces)} 个完成[/green]")
                
                # 跳过追踪步骤，直接进入步骤3
                console.print()
                console.print(Panel("[bold yellow]步骤 3: 创建审计任务...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
                
                try:
                    audit_agent = AuditAgent(llm_client=llm_client, max_workers=args.max_workers, attack_surface=attack_surface, project_type=project_type, debug=args.debug, code_dir=code_dir)
                    audit_tasks = audit_agent.create_audit_tasks_with_trace(complete_traces)    
                    
                    console.print(f"[green]创建了 {len(audit_tasks)} 个审计任务[/green]")
                except Exception as e:
                    #打印调用栈
                    import traceback
                    traceback.print_exc()
                    console.print(f"[bold red]错误: 创建审计任务失败: {str(e)}[/bold red]")
                    sys.exit(1)
                
                # 继续执行后续步骤
                
            except Exception as e:
                console.print(f"[bold red]错误: 加载追踪结果失败: {str(e)}[/bold red]")
                sys.exit(1)
    else:
        # 正常执行追踪步骤
        console.print()
        console.print(Panel("[bold yellow]步骤 2: 追踪外部输入数据流...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
        
        try:
            trace_agent = TraceAgent(
                llm_client=llm_client,
                max_workers=args.max_workers,
                enable_lsp=args.enable_lsp,
                project_type=project_type,
                attack_surface=attack_surface,
                code_dir=code_dir
            )
            
            trace_results = trace_agent.trace_functions_concurrent(functions)
            complete_traces = trace_agent.get_complete_traces_only(trace_results)
            
            # 保存追踪结果到文件
            try:
                trace_agent.save_trace_results(trace_results)
            except Exception as e:
                console.print(f"[yellow]⚠ 追踪结果保存失败: {str(e)}[/yellow]")
            
            try:
                report_path = trace_agent.generate_trace_report(trace_results)
                console.print(f"[green]✓ 追踪报告已生成: {report_path}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ 追踪报告生成失败: {str(e)}[/yellow]")
            
            if args.debug:
                console.print()
                console.print(Panel("[bold magenta]调试信息 - 追踪结果 (Trace Results)[/bold magenta]", box=box.ROUNDED, padding=(0, 1)))
                
                for i, trace_result in enumerate(trace_results, 1):
                    status_style = "green" if trace_result.trace_complete else "red"
                    status_text = "完成" if trace_result.trace_complete else "失败"
                    
                    table = Table(title=f"[追踪结果 {i}/{len(trace_results)}]", box=box.SIMPLE, show_header=True, header_style="bold cyan")
                    table.add_column("属性", style="cyan", width=15)
                    table.add_column("值", style="white")
                    
                    table.add_row("任务ID", trace_result.task_id)
                    table.add_row("文件路径", trace_result.function_info.file_path)
                    table.add_row("函数名", trace_result.function_info.function_name)
                    table.add_row("项目类型", trace_result.project_type)
                    table.add_row("攻击面", trace_result.attack_surface)
                    table.add_row("追踪状态", f"[{status_style}]{status_text}[/{status_style}]")
                    
                    if trace_result.error_message:
                        table.add_row("错误信息", f"[red]{trace_result.error_message}[/red]")
                    
                    table.add_row("代码逻辑", trace_result.code_logic)
                    table.add_row("代码地图条目数", str(len(trace_result.code_map)))
                    
                    console.print(table)
                    
                    if trace_result.code_map:
                        code_map_table = Table(title="代码地图详情", box=box.SIMPLE, show_header=True, header_style="bold yellow")
                        code_map_table.add_column("序号", style="cyan", width=6)
                        code_map_table.add_column("文件路径", style="blue")
                        code_map_table.add_column("行号", style="yellow")
                        code_map_table.add_column("上下文类型", style="green")
                        
                        for j, code_context in enumerate(trace_result.code_map, 1):
                            code_map_table.add_row(
                                str(j),
                                code_context.file_path,
                                f"{code_context.line_start}-{code_context.line_end}",
                                code_context.context_type
                            )
                        
                        console.print(code_map_table)
                    
                    if i < len(trace_results):
                        console.print()
                
                console.print()
            
        except Exception as e:
            # 捕获并打印追踪失败的详细信息
            if 'trace_results' in locals():
                for trace_result in trace_results:
                    console.print(f"[red]  函数 {trace_result.function_info.file_path}:追踪失败: {trace_result.error_message}[/red]")  

            console.print(f"[bold red]错误: 追踪失败: {str(e)}[/bold red]")
            sys.exit(1)
        
        if not complete_traces:
            console.print("[yellow]未完成任何追踪，审计结束[/yellow]")
            sys.exit(0)
        
        # 继续执行后续步骤
        console.print()
        console.print(Panel("[bold yellow]步骤 3: 创建审计任务...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
        
        try:
            audit_agent = AuditAgent(llm_client=llm_client, max_workers=args.max_workers, attack_surface=args.attack_surface, project_type=args.project_type, debug=args.debug, code_dir=code_dir)
            audit_tasks = audit_agent.create_audit_tasks_with_trace(complete_traces)
            
            console.print(f"[green]创建了 {len(audit_tasks)} 个审计任务[/green]")
        except Exception as e:
            console.print(f"[bold red]错误: 创建审计任务失败: {str(e)}[/bold red]")
            sys.exit(1)
    
    console.print()
    console.print(Panel("[bold yellow]步骤 4: 并发审计函数...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
    
    try:
        trace_results_map = {
            f"{trace.function_info.file_path}:{trace.function_info.function_name}": trace
            for trace in complete_traces
        }
        
        audit_results = audit_agent.audit_functions_concurrent(audit_tasks, trace_results_map)
        vulnerabilities = audit_agent.get_vulnerabilities_only(audit_results)
        
        console.print(f"[green]审计完成，发现 {len(vulnerabilities)} 个潜在漏洞[/green]")
        
        if args.verbose:
            table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
            table.add_column("序号", style="cyan", width=6)
            table.add_column("漏洞类型", style="red")
            table.add_column("严重程度", style="yellow")
            table.add_column("置信度", style="green")
            
            for i, vuln in enumerate(vulnerabilities, 1):
                severity_style = {
                    "Critical": "bold red",
                    "High": "red",
                    "Medium": "yellow",
                    "Low": "blue"
                }.get(vuln.severity, "white")
                
                table.add_row(
                    str(i),
                    vuln.vulnerability_type,
                    f"[{severity_style}]{vuln.severity}[/{severity_style}]",
                    f"{vuln.confidence:.2f}"
                )
            
            console.print(table)
    except Exception as e:
        # 捕获并打印审计失败的详细信息
        if 'audit_results' in locals():
            for audit_result in audit_results:
                console.print(f"[red]  函数 {audit_result.function_info.file_path}:审计失败: {audit_result.error_message}[/red]")
        #打印错误调用栈
        import traceback
        traceback.print_exc()

        console.print(f"[bold red]错误: 审计失败: {str(e)}[/bold red]")
        sys.exit(1)
    
    if not vulnerabilities:
        console.print("[yellow]未发现任何漏洞，审计结束[/yellow]")
        sys.exit(0)
    
    exploit_results = []
    
    if not args.skip_exploit:
        console.print()
        console.print(Panel("[bold yellow]步骤 5: 漏洞利用...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
        
        try:
            exploit_agent = ExploitAgent(llm_client=llm_client, debug=args.debug)
            
            for i, audit_result in enumerate(vulnerabilities, 1):
                console.print(f"尝试利用漏洞 [cyan]{i}/{len(vulnerabilities)}[/cyan]: [red]{audit_result.vulnerability_type}[/red]")
                
                function_code = audit_result.function_info.code_snippet
                exploit_result = exploit_agent.exploit_vulnerability(
                    audit_result,
                    function_code,
                    attack_surface
                )
                
                exploit_results.append(exploit_result)
                
                if exploit_result.exploit_successful:
                    console.print(f"  [green]✓ 漏洞利用成功[/green]")
                else:
                    console.print(f"  [red]✗ 漏洞利用失败: {exploit_result.error_message or '未知原因'}[/red]")
            
            successful_exploits = [r for r in exploit_results if r.exploit_successful]
            console.print(f"[green]漏洞利用完成，成功利用 {len(successful_exploits)}/{len(vulnerabilities)} 个漏洞[/green]")
        except Exception as e:
            console.print(f"[bold red]错误: 漏洞利用失败: {str(e)}[/bold red]")
            exploit_results = []
    else:
        console.print("[yellow]跳过漏洞利用步骤[/yellow]")
        exploit_results = []
    
    console.print()
    console.print(Panel("[bold yellow]步骤 6: 生成报告...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))
    
    try:
        report_agent = ReportAgent(llm_client=llm_client, output_dir=args.output_dir)
        
        if args.report_format in ['markdown', 'all']:
            report_path = report_agent.generate_report(exploit_results, code_dir, args.attack_surface)
            console.print(f"[green]Markdown报告已生成: {report_path}[/green]")
        
        if args.report_format in ['json', 'all']:
            report_path = report_agent.generate_json_report(exploit_results, code_dir, args.attack_surface)
            console.print(f"[green]JSON报告已生成: {report_path}[/green]")
        
        if args.report_format in ['html', 'all']:
            report_path = report_agent.generate_html_report(exploit_results, code_dir, args.attack_surface)
            console.print(f"[green]HTML报告已生成: {report_path}[/green]")
    except Exception as e:
        console.print(f"[bold red]错误: 报告生成失败: {str(e)}[/bold red]")
        sys.exit(1)
    
    console.print()
    console.print(Panel("[bold green]审计完成！[/bold green]", box=box.DOUBLE, padding=(1, 3)))


if __name__ == '__main__':
    main()
