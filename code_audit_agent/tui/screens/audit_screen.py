"""审计界面"""

from textual.screen import Screen
from textual.widgets import Static, Button, Input, Checkbox, Label, TextArea
from textual.containers import Container, Vertical, Horizontal
from textual.message import Message
from textual import work
from typing import Optional, List
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))

from code_audit_agent.tui.widgets.agent_flow import AgentFlow
from code_audit_agent.tui.widgets.message_container import MessageLog
from code_audit_agent.tui.state import AppState
from code_audit_agent.scanners import FunctionScanner
from code_audit_agent.agents import AuditAgent, ExploitAgent, ReportAgent, TraceAgent
from code_audit_agent.utils import LLMClient
from code_audit_agent.utils.config import get_config
from code_audit_agent.utils.models import FunctionInfo, TraceResult, AuditResult


class AuditScreen(Screen):
    CSS = """
    #bottom_input {
        height: auto;
        margin: 1;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }

    #bottom_input TextArea {
        min-width: 20; 
        margin-right: 1;
        overflow: auto;
        min-height: 3;
        max-height: 10;
    }
    
    #messages_log{
        height: 1fr;
        min-height: 20;
    }
    """
    
    class InterruptRequest(Message):
        def __init__(self, prompt: str):
            self.prompt = prompt
            super().__init__()
    
    def __init__(self):
        super().__init__()
        self.app_state = AppState()
        self.config = get_config()
        self.llm_client: Optional[LLMClient] = None
        self.interrupt_mode = False
        self.current_input: Optional[str] = None
        self.is_receiving_response = False
        
        self.scanner = None
        self.trace_agent = None
        self.audit_agent = None
        self.exploit_agent = None
        self.report_agent = None
        
        self.functions: List[FunctionInfo] = []
        self.trace_results: List[TraceResult] = []
        self.audit_results: List[AuditResult] = []
        self.exploit_results: List = []
        
        self.current_streaming_message = None
        self.current_streaming_content = ""
    
    def compose(self) -> None:
        yield Static("代码审计AI Agent - 审计中", id="audit_title")
        
        with Vertical(id="main_content"):
            yield Static("配置信息", id="config_label")
            yield Static("", id="config_info")
            
            yield AgentFlow(
                agents=["scanner", "trace_agent", "audit_agent", "exploit_agent", "report_agent"],
                id="agent_flow"
            )
            
            yield Static("LLM对话", id="messages_label")
            yield MessageLog(id="messages_log")
            
            with Horizontal(id="bottom_input"):
                yield Input(placeholder="输入消息...", id="user_input")
                yield Checkbox("干扰模式", id="interrupt_checkbox")
                yield Button("发送", id="send_button")
        
        yield Static("按 Ctrl+C 退出", id="footer")
    
    def on_mount(self) -> None:
        code_dir = self.app_state.audit_config.code_dir
        project_type = self.app_state.audit_config.project_types[0] if self.app_state.audit_config.project_types else "N/A"
        attack_surface = self.app_state.audit_config.attack_surfaces[0] if self.app_state.audit_config.attack_surfaces else "N/A"
        
        self.app_state.reset()
        
        for agent in ["scanner", "trace_agent", "audit_agent", "exploit_agent", "report_agent"]:
            self.app_state.add_agent(agent)
        
        self.app_state.audit_config.code_dir = code_dir
        self.app_state.audit_config.project_types = [project_type]
        self.app_state.audit_config.attack_surfaces = [attack_surface]
        
        self.query_one("#interrupt_checkbox", Checkbox).value = self.app_state.audit_config.interrupt_mode
        
        config_text = f"代码目录: {code_dir} | 项目类型: {project_type} | 攻击面: {attack_surface}"
        self.query_one("#config_info", Static).update(config_text)
        
        self.llm_client = LLMClient(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
            model=self.config.model,
            debug=self.config.debug
        )
        
        self.app_state.is_running = True
        self.run_audit()
    
    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if event.checkbox.id == "interrupt_checkbox":
            self.interrupt_mode = event.checkbox.value
            self.app_state.audit_config.interrupt_mode = event.checkbox.value
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send_button":
            self._send_user_input()
    
    def _send_user_input(self):
        input_widget = self.query_one("#user_input", TextArea)
        user_input = input_widget.text.strip()
        
        if user_input:
            self._add_message("user", user_input)
            input_widget.text = ""
            
            input_widget.disabled = False
            self.query_one("#send_button", Button).disabled = False
            self.is_receiving_response = False
            
            self._continue_llm_conversation()
    
    def _add_message(self, role: str, content: str):
        """添加消息（线程安全）"""
        def _do_add():
            message_log = self.query_one("#messages_log", MessageLog)
            message_log.add_message(role, content)
            message_log.scroll_end()
        self.call_later(_do_add)
    
    def _start_streaming_message(self, role: str = "assistant"):
        """开始流式消息（线程安全）"""
        def _do_start():
            message_log = self.query_one("#messages_log", MessageLog)
            self.current_streaming_message = message_log.add_message(role, "")
            self.current_streaming_content = ""
        self.call_later(_do_start)
    
    def _update_streaming_message(self, chunk: str):
        """更新流式消息（线程安全）"""
        def _do_update():
            if self.current_streaming_message:
                self.current_streaming_content += chunk
                self.current_streaming_message.content = self.current_streaming_content
                message_log = self.query_one("#messages_log", MessageLog)
                message_log.update_message(self.current_streaming_message, self.current_streaming_content)
        self.call_later(_do_update)
    
    def _finish_streaming_message(self):
        if self.current_streaming_message:
            self.current_streaming_message.collapsed = True
            self.current_streaming_message = None
            self.current_streaming_content = ""
    
    def _update_agent_flow(self, agent_index: int):
        """更新 Agent 流程（线程安全）"""
        def _do_update():
            agent_flow = self.query_one("#agent_flow", AgentFlow)
            agent_flow.update_agent_status(agent_index)
        self.call_later(_do_update)
    
    @work(thread=True, exclusive=True)
    def run_audit(self):
        try:
            self._update_agent_flow(0)
            
            code_dir = self.app_state.audit_config.code_dir
            project_type = self.app_state.audit_config.project_types[0] if self.app_state.audit_config.project_types else "python"
            attack_surface = self.app_state.audit_config.attack_surfaces[0] if self.app_state.audit_config.attack_surfaces else "web"
            
            self._add_message("system", f"开始审计\n代码目录: {code_dir}\n项目类型: {project_type}\n攻击面: {attack_surface}")
            
            self._run_scanner(code_dir, project_type, attack_surface)
            
            self._run_trace(code_dir, project_type, attack_surface)
            
            self._run_audit(code_dir, project_type, attack_surface)
            
            if not self.config.skip_exploit:
                self._run_exploit(code_dir)
            
            self._run_report(code_dir, attack_surface)
            
            self._add_message("system", "审计完成!")
            self._update_agent_flow(4)
            
        except Exception as e:
            self._add_message("system", f"审计失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _run_scanner(self, code_dir: str, project_type: str, attack_surface: str):
        self._add_message("system", "步骤 1: 扫描接口函数...")
        self._update_agent_flow(0)
        
        self.scanner = FunctionScanner()
        self.functions = self.scanner.scan_functions(code_dir, project_type, attack_surface)
        
        self._add_message("system", f"扫描完成，发现 {len(self.functions)} 个接口函数")
        
        if not self.functions:
            raise Exception("未发现任何接口函数")
    
    def _run_trace(self, code_dir: str, project_type: str, attack_surface: str):
        self._add_message("system", "步骤 2: 追踪外部输入数据流...")
        self._update_agent_flow(1)
        
        self.trace_agent = TraceAgent(
            llm_client=self.llm_client,
            max_workers=self.config.max_workers,
            enable_lsp=self.config.enable_lsp,
            project_type=project_type,
            attack_surface=attack_surface,
            code_dir=code_dir
        )
        
        self.trace_results = self.trace_agent.trace_functions_concurrent(self.functions)
        
        complete_traces = [t for t in self.trace_results if t.trace_complete]
        self._add_message("system", f"追踪完成，{len(complete_traces)}/{len(self.trace_results)} 个追踪成功")
        
        if not complete_traces:
            raise Exception("未完成任何追踪")
    
    def _run_audit(self, code_dir: str, project_type: str, attack_surface: str):
        self._add_message("system", "步骤 3-4: 并发审计函数...")
        self._update_agent_flow(2)
        
        self.audit_agent = AuditAgent(
            llm_client=self.llm_client,
            max_workers=self.config.max_workers,
            attack_surface=attack_surface,
            project_type=project_type,
            code_dir=code_dir
        )
        
        complete_traces = [t for t in self.trace_results if t.trace_complete]
        audit_tasks = self.audit_agent.create_audit_tasks_with_trace(complete_traces)
        
        trace_results_map = {
            f"{trace.function_info.file_path}:{trace.function_info.function_name}": trace
            for trace in complete_traces
        }
        
        self.audit_results = self.audit_agent.audit_functions_concurrent(audit_tasks, trace_results_map)
        
        vulnerabilities = self.audit_agent.get_vulnerabilities_only(self.audit_results)
        self._add_message("system", f"审计完成，发现 {len(vulnerabilities)} 个潜在漏洞")
        
        if not vulnerabilities:
            raise Exception("未发现任何漏洞")
    
    def _run_exploit(self, code_dir: str):
        self._add_message("system", "步骤 5: 漏洞利用...")
        self._update_agent_flow(3)
        
        self.exploit_agent = ExploitAgent(
            llm_client=self.llm_client,
            code_dir=code_dir
        )
        
        vulnerabilities = self.audit_agent.get_vulnerabilities_only(self.audit_results)
        
        self.exploit_results = []
        for i, audit_result in enumerate(vulnerabilities, 1):
            self._add_message("system", f"尝试利用漏洞 {i}/{len(vulnerabilities)}: {audit_result.vulnerability_type}")
            
            function_code = audit_result.function_info.code_snippet
            exploit_result = self.exploit_agent.exploit_vulnerability(audit_result, function_code)
            self.exploit_results.append(exploit_result)
            
            if exploit_result.exploit_successful:
                self._add_message("system", f"  ✓ 漏洞利用成功")
            else:
                self._add_message("system", f"  ✗ 漏洞利用失败: {exploit_result.error_message or '未知原因'}")
        
        successful = len([r for r in self.exploit_results if r.exploit_successful])
        self._add_message("system", f"漏洞利用完成，成功 {successful}/{len(vulnerabilities)} 个")
    
    def _run_report(self, code_dir: str, attack_surface: str):
        self._add_message("system", "步骤 6: 生成报告...")
        self._update_agent_flow(4)
        
        self.report_agent = ReportAgent(
            llm_client=self.llm_client,
            output_dir=self.config.output_dir
        )
        
        report_path = self.report_agent.generate_report(
            self.exploit_results if self.exploit_results else [],
            code_dir,
            attack_surface
        )
        
        self._add_message("system", f"报告已生成: {report_path}")
    
    def _continue_llm_conversation(self):
        pass
