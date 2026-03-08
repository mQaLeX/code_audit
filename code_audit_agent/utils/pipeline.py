import os
import traceback
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from code_audit_agent.agents import (
    AuditAgent, ExploitAgent, ReportAgent, TraceAgent
)
from code_audit_agent.scanners import FunctionScanner
from code_audit_agent.utils import LLMClient
from code_audit_agent.utils.models import (
    AuditResult, ExploitResult, TraceResult
)
from code_audit_agent.utils.session_manager import SessionManager


console = Console()


class Pipeline:
    STAGES = ['scanner', 'trace', 'audit', 'exploit', 'report']

    def __init__(self, session: SessionManager, config: Any, docker_manager=None, llm_client: LLMClient = None):
        self.session = session
        self.config = config
        self.llm_client = llm_client
        self.code_dir = config.code_dir
        self.docker_manager = docker_manager

        self.scanner = None
        self.trace_agent = None
        self.audit_agent = None
        self.exploit_agent = None
        self.report_agent = None

    def run(self, from_stage: str = None) -> bool:
        if from_stage is None:
            from_stage = self.session.get_next_stage()

        if not self._ensure_llm_client():
            return False

        self._print_header()

        stage_index = self.STAGES.index(from_stage) if from_stage in self.STAGES else 0

        try:
            if stage_index <= 0:
                if not self._run_scanner():
                    return False

            if stage_index <= 1:
                if not self._run_trace():
                    return False

            if stage_index <= 2:
                if not self._run_audit():
                    return False

            if stage_index <= 3:
                if not self._run_exploit():
                    return False

            if stage_index <= 4:
                if not self._run_report():
                    return False

            self._print_success()
            return True

        except Exception as e:
            console.print(f"[bold red]流水线执行失败: {str(e)}[/bold red]")
            console.print(traceback.format_exc())
            return False

    def _ensure_llm_client(self) -> bool:
        if self.llm_client is None:
            try:
                self.llm_client = LLMClient(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                    model=self.config.model,
                    debug=self.config.debug
                )
                console.print("[green]✓ LLM客户端初始化成功[/green]")
            except Exception as e:
                console.print(f"[bold red]错误: LLM客户端初始化失败: {str(e)}[/bold red]")
                return False
        return True

    def _print_header(self):
        panel = Panel(
            f"""[cyan]代码目录:[/cyan] {self.code_dir}
[cyan]项目类型:[/cyan] {self.config.project_type}
[cyan]攻击面:[/cyan] {self.config.attack_surface}
[cyan]会话ID:[/cyan] {self.session.session_id}
[cyan]LLM模型:[/cyan] {self.config.model}
[cyan]并发线程数:[/cyan] {self.config.max_workers}
[cyan]跳过漏洞利用:[/cyan] {self.config.skip_exploit}
[cyan]调试模式:[/cyan] {self.config.debug}""",
            title="[bold blue]代码审计AI Agent[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        )
        console.print(panel)
        console.print()

    def _run_scanner(self) -> bool:
        console.print(Panel("[bold yellow]步骤 1: 扫描接口函数...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        if self.session.has_results('scanner'):
            console.print("[yellow]从检查点加载扫描结果...[/yellow]")
            functions = self.session.load_data('scanner')
            console.print(f"[green]✓ 已加载 {len(functions)} 个接口函数[/green]")
        else:
            try:
                scanner = FunctionScanner()
                functions = scanner.scan_functions(
                    self.code_dir,
                    self.config.project_type,
                    self.config.attack_surface
                )

                console.print(f"[green]扫描完成，发现 {len(functions)} 个接口函数[/green]")

                if self.config.verbose:
                    self._print_functions_table(functions)

                self.session.save('scanner', [
                    {
                        'file_path': f.file_path,
                        'function_name': f.function_name,
                        'code_snippet': f.code_snippet
                    }
                    for f in functions
                ])
                console.print(f"[green]✓ 扫描结果已保存到会话[/green]")

            except Exception as e:
                console.print(f"[bold red]错误: 函数扫描失败: {str(e)}[/bold red]")
                return False

        if not functions:
            console.print("[yellow]未发现任何接口函数，审计结束[/yellow]")
            return False

        return True

    def _run_trace(self) -> bool:
        console.print(Panel("[bold yellow]步骤 2: 追踪外部输入数据流...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        if self.session.has_results('trace'):
            console.print("[yellow]从检查点加载追踪结果...[/yellow]")
            trace_results = self.session.load_data('trace')
            complete_traces = [t for t in trace_results if t.trace_complete]
            console.print(f"[green]✓ 已加载 {len(trace_results)} 个追踪结果，其中 {len(complete_traces)} 个完成[/green]")
        else:
            try:
                functions = self.session.load_data('scanner')

                trace_agent = TraceAgent(
                    llm_client=self.llm_client,
                    max_workers=self.config.max_workers,
                    enable_lsp=self.config.enable_lsp,
                    project_type=self.config.project_type,
                    attack_surface=self.config.attack_surface,
                    code_dir=self.code_dir,
                    docker_manager=self.docker_manager
                )

                trace_results = trace_agent.trace_functions_concurrent(functions)
                complete_traces = [t for t in trace_results if t.trace_complete]

                self.session.save('trace', trace_results)
                console.print(f"[green]✓ 追踪结果已保存到会话[/green]")

                try:
                    report_path = trace_agent.generate_trace_report(trace_results)
                    console.print(f"[green]✓ 追踪报告已生成: {report_path}[/green]")
                except Exception as e:
                    console.print(f"[yellow]⚠ 追踪报告生成失败: {str(e)}[/yellow]")

                if self.config.debug:
                    self._print_trace_debug(trace_results)

            except Exception as e:
                console.print(f"[bold red]错误: 追踪失败: {str(e)}[/bold red]")
                return False

        if not complete_traces:
            console.print("[yellow]未完成任何追踪，审计结束[/yellow]")
            return False

        return True

    def _run_audit(self) -> bool:
        console.print(Panel("[bold yellow]步骤 3: 创建审计任务...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        try:
            trace_results = self.session.load_data('trace')
            complete_traces = [t for t in trace_results if t.trace_complete]

            audit_agent = AuditAgent(
                llm_client=self.llm_client,
                max_workers=self.config.max_workers,
                attack_surface=self.config.attack_surface,
                project_type=self.config.project_type,
                code_dir=self.code_dir,
                docker_manager=self.docker_manager
            )

            audit_tasks = audit_agent.create_audit_tasks_with_trace(complete_traces)
            console.print(f"[green]创建了 {len(audit_tasks)} 个审计任务[/green]")

        except Exception as e:
            console.print(f"[bold red]错误: 创建审计任务失败: {str(e)}[/bold red]")
            return False

        console.print(Panel("[bold yellow]步骤 4: 并发审计函数...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        try:
            trace_results_map = {
                f"{trace.function_info.file_path}:{trace.function_info.function_name}": trace
                for trace in complete_traces
            }

            audit_results = audit_agent.audit_functions_concurrent(audit_tasks, trace_results_map)
            vulnerabilities = audit_agent.get_vulnerabilities_only(audit_results)

            console.print(f"[green]审计完成，发现 {len(vulnerabilities)} 个潜在漏洞[/green]")

            self.session.save('audit', audit_results)
            console.print(f"[green]✓ 审计结果已保存到会话[/green]")

            try:
                html_report_path = audit_agent.generate_audit_html_report(
                    audit_results, self.config.attack_surface, self.code_dir
                )
                console.print(f"[green]✓ 审计 HTML 报告已生成: {html_report_path}[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠ 审计 HTML 报告生成失败: {str(e)}[/yellow]")

            if self.config.verbose:
                self._print_vulnerabilities_table(vulnerabilities)

        except Exception as e:
            console.print(f"[bold red]错误: 审计失败: {str(e)}[/bold red]")
            console.print(traceback.format_exc())
            return False

        if not vulnerabilities:
            console.print("[yellow]未发现任何漏洞，审计结束[/yellow]")
            return False

        return True

    def _run_exploit(self) -> bool:
        if self.config.skip_exploit:
            console.print("[yellow]跳过漏洞利用步骤[/yellow]")
            return True

        console.print(Panel("[bold yellow]步骤 5: 漏洞利用...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        try:
            audit_results = self.session.load_data('audit')
            vulnerabilities = [r for r in audit_results if r.has_vulnerability]

            exploit_agent = ExploitAgent(
                llm_client=self.llm_client,
                code_dir=self.code_dir,
                docker_manager=self.docker_manager
            )

            exploit_results = []
            for i, audit_result in enumerate(vulnerabilities, 1):
                console.print(f"尝试利用漏洞 [cyan]{i}/{len(vulnerabilities)}[/cyan]: [red]{audit_result.vulnerability_type}[/red]")

                function_code = audit_result.function_info.code_snippet
                exploit_result = exploit_agent.exploit_vulnerability(
                    audit_result,
                    function_code
                )

                exploit_results.append(exploit_result)

                if exploit_result.exploit_successful:
                    console.print(f"  [green]✓ 漏洞利用成功[/green]")
                else:
                    console.print(f"  [red]✗ 漏洞利用失败: {exploit_result.error_message or '未知原因'}[/red]")

            successful_exploits = [r for r in exploit_results if r.exploit_successful]
            console.print(f"[green]漏洞利用完成，成功利用 {len(successful_exploits)}/{len(vulnerabilities)} 个漏洞[/green]")

            self.session.save('exploit', exploit_results)
            console.print(f"[green]✓ 漏洞利用结果已保存到会话[/green]")

        except Exception as e:
            console.print(f"[bold red]错误: 漏洞利用失败: {str(e)}[/bold red]")
            console.print(traceback.format_exc())
            return False

        return True

    def _run_report(self) -> bool:
        console.print(Panel("[bold yellow]步骤 6: 生成报告...[/bold yellow]", box=box.SIMPLE, padding=(0, 1)))

        try:
            exploit_results = []
            if self.session.has_results('exploit'):
                exploit_results = self.session.load_data('exploit')

            report_agent = ReportAgent(
                llm_client=self.llm_client,
                output_dir=self.config.output_dir
            )

            report_path = report_agent.generate_report(
                exploit_results,
                self.code_dir,
                self.config.attack_surface
            )

            console.print(f"[green]Markdown报告已生成: {report_path}[/green]")

        except Exception as e:
            console.print(f"[bold red]错误: 报告生成失败: {str(e)}[/bold red]")
            console.print(traceback.format_exc())
            return False

        return True

    def _print_success(self):
        console.print()
        console.print(Panel("[bold green]审计完成！[/bold green]", box=box.DOUBLE, padding=(1, 3)))

    def _print_functions_table(self, functions: List):
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("序号", style="cyan", width=6)
        table.add_column("文件路径", style="blue")
        table.add_column("函数名", style="green")
        table.add_column("行号", style="yellow")

        for i, func in enumerate(functions, 1):
            line_info = f"{func.line_start}-{func.line_end}" if hasattr(func, 'line_start') else "N/A"
            table.add_row(str(i), func.file_path, func.function_name, line_info)

        console.print(table)

    def _print_vulnerabilities_table(self, vulnerabilities: List[AuditResult]):
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        table.add_column("序号", style="cyan", width=6)
        table.add_column("漏洞类型", style="red")
        table.add_column("严重程度", style="yellow")
        table.add_column("置信度", style="green")

        severity_style = {
            "Critical": "bold red",
            "High": "red",
            "Medium": "yellow",
            "Low": "blue"
        }

        for i, vuln in enumerate(vulnerabilities, 1):
            style = severity_style.get(vuln.severity, "white")
            table.add_row(
                str(i),
                vuln.vulnerability_type,
                f"[{style}]{vuln.severity}[/{style}]",
                f"{vuln.confidence:.2f}"
            )

        console.print(table)

    def _print_trace_debug(self, trace_results: List[TraceResult]):
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
