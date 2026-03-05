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
import traceback

from code_audit_agent.utils import LLMClient
from code_audit_agent.utils.config import get_config
from code_audit_agent.scanners import FunctionScanner
from code_audit_agent.agents import AuditAgent, ExploitAgent, ReportAgent, TraceAgent
from code_audit_agent.utils.session_manager import SessionManager
from code_audit_agent.utils.pipeline import Pipeline


console = Console()


def get_knowledge_base_dir():
    return os.path.join(os.path.dirname(__file__), 'code_audit_agent', 'knowledge')


def get_project_types():
    knowledge_dir = get_knowledge_base_dir()
    project_types = []
    
    if os.path.exists(knowledge_dir):
        for item in os.listdir(knowledge_dir):
            if os.path.isdir(os.path.join(knowledge_dir, item)):
                project_types.append(item)
    
    return sorted(project_types)


def get_attack_surfaces(project_type: str):
    knowledge_dir = get_knowledge_base_dir()
    project_dir = os.path.join(knowledge_dir, project_type)
    
    attack_surfaces = []
    
    if os.path.exists(project_dir):
        for item in os.listdir(project_dir):
            if os.path.isdir(os.path.join(project_dir, item)):
                attack_surfaces.append(item)
    
    return sorted(attack_surfaces)


def get_vulnerability_types(project_type: str, attack_surface: str):
    knowledge_dir = get_knowledge_base_dir()
    vuln_dir = os.path.join(knowledge_dir, project_type, attack_surface)
    
    vuln_types = []
    
    if os.path.exists(vuln_dir):
        for item in os.listdir(vuln_dir):
            if item.endswith('.txt'):
                vuln_types.append(item[:-4])
    
    return sorted(vuln_types)


def validate_code_directory(code_dir: str) -> bool:
    if not os.path.exists(code_dir):
        console.print(f"[bold red]错误: 代码目录不存在: {code_dir}[/bold red]")
        return False
    
    if not os.path.isdir(code_dir):
        console.print(f"[bold red]错误: 路径不是目录: {code_dir}[/bold red]")
        return False
    
    return True


def list_project_types():
    project_types = get_project_types()
    
    table = Table(title="支持的项目类型 (Project Types)", box=box.ROUNDED)
    table.add_column("序号", style="cyan", justify="right")
    table.add_column("项目类型", style="green")
    
    for i, pt in enumerate(project_types, 1):
        table.add_row(str(i), pt)
    
    console.print(table)


def list_attack_surfaces(project_type: str):
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


def list_sessions():
    sessions = SessionManager.list_sessions()
    
    if not sessions:
        console.print("[yellow]暂无历史会话[/yellow]")
        return
    
    table = Table(title="历史会话", box=box.ROUNDED)
    table.add_column("会话ID", style="green")
    table.add_column("项目类型", style="cyan")
    table.add_column("攻击面", style="yellow")
    table.add_column("代码目录", style="blue")
    table.add_column("创建时间", style="magenta")
    table.add_column("完成阶段", style="white")
    
    for session in sessions:
        metadata = session.get('completed_stages', [])
        completed = ', '.join(metadata) if metadata else '无'
        
        table.add_row(
            session.get('session_id', 'N/A'),
            session.get('project_type', 'N/A'),
            session.get('attack_surface', 'N/A'),
            session.get('code_dir', 'N/A')[:50] + '...' if len(session.get('code_dir', '')) > 50 else session.get('code_dir', 'N/A'),
            session.get('created_at', 'N/A')[:19],
            completed
        )
    
    console.print(table)
    console.print("\n[bold]使用方法:[/bold]")
    console.print("  python main.py --session <会话ID>")
    console.print("  python main.py --session <会话ID> --from-stage trace")


def list_result_files(result_type: str):
    sessions = SessionManager.list_sessions()
    
    if not sessions:
        console.print(f"[yellow]暂无 {result_type} 结果文件[/yellow]")
        return
    
    table = Table(title=f"{result_type} 结果文件", box=box.ROUNDED)
    table.add_column("会话ID", style="green")
    table.add_column("项目类型", style="cyan")
    table.add_column("攻击面", style="yellow")
    table.add_column("创建时间", style="magenta")
    
    has_results = False
    for session in sessions:
        session_mgr = SessionManager.load(session['session_id'])
        if session_mgr.has_results(result_type):
            has_results = True
            table.add_row(
                session['session_id'],
                session.get('project_type', 'N/A'),
                session.get('attack_surface', 'N/A'),
                session.get('created_at', 'N/A')[:19]
            )
    
    if not has_results:
        console.print(f"[yellow]暂无 {result_type} 结果文件[/yellow]")
        return
    
    console.print(table)


def handle_list_commands(config):
    if config.list_type == 'sessions' or (not config.project_type and not config.session_id):
        list_sessions()
        return True
    
    if config.session_id:
        session = SessionManager.load(config.session_id)
        if not session:
            console.print(f"[bold red]错误: 会话不存在: {config.session_id}[/bold red]")
            return True
        
        if config.list_type == 'trace':
            list_result_files('trace')
            return True
        elif config.list_type == 'audit':
            list_result_files('audit')
            return True
        elif config.list_type == 'exploit':
            list_result_files('exploit')
            return True
    
    return False


def main():
    config = get_config()
    
    if config.list_type == 'sessions' or (config.list_type and not config.project_type):
        list_sessions()
        sys.exit(0)
    
    if config.list_type == 'trace' or config.list_type == 'audit' or config.list_type == 'exploit':
        if config.session_id:
            list_result_files(config.list_type)
        else:
            list_sessions()
            console.print(f"\n[yellow]提示: 使用 --session <会话ID> {config.list_type} 查看特定会话的{config.list_type}结果[/yellow]")
        sys.exit(0)
    
    if config.project_type == 'list':
        list_project_types()
        sys.exit(0)
    
    if config.attack_surface == 'list':
        list_attack_surfaces(config.project_type)
        sys.exit(0)
    
    if config.list_type == 'list':
        list_vulnerability_types(config.project_type, config.attack_surface)
        sys.exit(0)
    
    if not config.session_id:
        code_dir = config.code_dir if config.code_dir else config.list_type
        code_dir = os.path.abspath(code_dir)
        
        if not code_dir:
            console.print("[bold red]错误: 请提供代码目录路径[/bold red]")
            console.print("使用方法: python main.py <project_type> <attack_surface> <code_dir>")
            console.print("使用 'python main.py list' 查看支持的类型")
            console.print("或使用 'python main.py --session <会话ID>' 恢复历史会话")
            sys.exit(1)
        
        if not validate_code_directory(code_dir):
            sys.exit(1)
        
        config.code_dir = code_dir
        session = SessionManager.create(
            project_type=config.project_type,
            attack_surface=config.attack_surface,
            code_dir=code_dir
        )
        console.print(f"[green]✓ 创建新会话: {session.session_id}[/green]")
    else:
        session = SessionManager.load(config.session_id)
        if not session:
            console.print(f"[bold red]错误: 会话不存在: {config.session_id}[/bold red]")
            sys.exit(1)
        
        metadata = session._load_metadata()
        config.project_type = metadata.get('project_type', config.project_type)
        config.attack_surface = metadata.get('attack_surface', config.attack_surface)
        config.code_dir = metadata.get('code_dir', '')
        
        console.print(f"[green]✓ 加载会话: {session.session_id}[/green]")
        
        latest_stage = session.get_latest_completed_stage()
        if latest_stage:
            console.print(f"[cyan]当前进度: 已完成 {latest_stage} 阶段[/cyan]")
            console.print(f"[cyan]下一步: {session.get_next_stage()} 阶段[/cyan]")
    
    from_stage = config.from_stage if hasattr(config, 'from_stage') and config.from_stage else None
    
    pipeline = Pipeline(session, config)
    
    success = pipeline.run(from_stage=from_stage)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]程序已被用户中断[/bold yellow]")
        sys.exit(130)
