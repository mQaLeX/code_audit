from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class FunctionInfo:
    file_path: str
    code_snippet: str
    function_name: str
    


@dataclass
class AuditTask:
    task_id: str
    function_info: FunctionInfo
    attack_surface: str
    question_type: str
    question: str


@dataclass
class AuditResult:
    task_id: str
    has_vulnerability: bool
    function_info: FunctionInfo
    vulnerability_type: Optional[str] = None
    severity: Optional[str] = None
    description: Optional[str] = None
    evidence: Optional[str] = None
    suggested_fix: Optional[str] = None
    confidence: float = 0.0


@dataclass
class ExploitResult:
    audit_result: AuditResult
    exploit_successful: bool
    exploit_script: Optional[str] = None
    exploit_output: Optional[str] = None
    exploit_screenshot: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class VulnerabilityReport:
    vulnerability_type: str
    file_path: str
    function_name: str
    line_number: int
    description: str
    exploit_script: Optional[str] = None
    exploit_screenshot: Optional[str] = None
    impact: str = ""
    cvss_score: float = 0.0
    cvss_vector: str = ""
    severity: str = ""


@dataclass
class CodeContext:
    file_path: str
    line_start: int
    line_end: int
    code_snippet: str
    context_type: str = "function"


@dataclass
class TraceResult:
    """
    函数追踪结果数据模型

    包含函数的详细信息、攻击面、项目类型、代码逻辑、是否完成、错误信息以及代码地图。
    full_msg 保存历史llm对话记录
    """
    task_id: str
    function_info: FunctionInfo
    attack_surface: str
    project_type: str
    code_logic: str
    trace_complete: bool = True
    error_message: Optional[str] = None
    full_msg: Optional[str] = None
    code_map: List[CodeContext] = field(default_factory=list)


