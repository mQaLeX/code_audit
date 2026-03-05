"""TUI集成模块"""

import os
import sys
from typing import List, Dict, Any, Optional

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from code_audit_agent.scanners import FunctionScanner
from code_audit_agent.agents import AuditAgent, ExploitAgent, ReportAgent, TraceAgent
from code_audit_agent.utils import LLMClient
from code_audit_agent.utils.config import get_config
from code_audit_agent.tui.state import AppState


class AuditRunner:
    """审计运行器，集成所有业务逻辑"""
    
    def __init__(self, app_state: AppState):
        self.app_state = app_state
        self.config = get_config()
        self.llm_client = LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
            debug=self.config.debug
        )
        self.scanner = FunctionScanner()
    
    def run_scanner(self, code_dir: str, project_types: List[str], attack_surfaces: List[str]) -> List[Dict[str, Any]]:
        """运行扫描器"""
        self.app_state.set_current_agent("scanner")
        
        # 这里需要实现扫描逻辑
        # 由于需要处理多个项目类型和攻击面，这里提供伪代码
        functions = []
        
        for project_type in project_types:
            for attack_surface in attack_surfaces:
                try:
                    # 扫描函数
                    funcs = self.scanner.scan_functions(code_dir, project_type, attack_surface)
                    functions.extend(funcs)
                except Exception as e:
                    # 记录错误
                    pass
        
        return functions
    
    def run_trace_agent(self, functions: List[Any]) -> List[Any]:
        """运行追踪Agent"""
        self.app_state.set_current_agent("trace_agent")
        
        # 这里需要实现追踪逻辑
        # 由于篇幅限制，这里提供伪代码
        trace_results = []
        
        for func in functions:
            # 创建追踪任务
            # 调用LLM进行追踪
            # 收集追踪结果
            pass
        
        return trace_results
    
    def run_audit_agent(self, trace_results: List[Any]) -> List[Any]:
        """运行审计Agent"""
        self.app_state.set_current_agent("audit_agent")
        
        audit_agent = AuditAgent(
            llm_client=self.llm_client,
            max_workers=self.config.max_workers,
            attack_surface="web",  # 需要从配置中获取
            project_type="c",  # 需要从配置中获取
            code_dir=self.app_state.audit_config.code_dir
        )
        
        # 创建审计任务
        tasks = audit_agent.create_audit_tasks_with_trace(trace_results)
        
        # 执行审计
        audit_results = []
        for task in tasks:
            result = audit_agent.audit_function(task)
            audit_results.append(result)
        
        return audit_results
    
    def run_exploit_agent(self, audit_results: List[Any]) -> List[Any]:
        """运行利用Agent"""
        self.app_state.set_current_agent("exploit_agent")
        
        exploit_agent = ExploitAgent(
            llm_client=self.llm_client,
            code_dir=self.app_state.audit_config.code_dir
        )
        
        # 执行利用
        exploit_results = []
        for result in audit_results:
            if result.has_vulnerability:
                exploit_result = exploit_agent.exploit_vulnerability(
                    result,
                    result.function_info.code_snippet
                )
                exploit_results.append(exploit_result)
        
        return exploit_results
    
    def run_report_agent(self, exploit_results: List[Any]) -> str:
        """运行报告Agent"""
        self.app_state.set_current_agent("report_agent")
        
        report_agent = ReportAgent(
            llm_client=self.llm_client,
            output_dir=self.config.output_dir
        )
        
        # 生成报告
        report_path = report_agent.generate_report(
            exploit_results,
            self.app_state.audit_config.code_dir,
            "web"  # 需要从配置中获取
        )
        
        return report_path
