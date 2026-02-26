import json
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid

from ..utils.models import (
    AuditTask,
    AuditResult,
    FunctionInfo,
    TraceResult,
    CodeContext
)
from ..utils.llm_client import LLMClient


class AuditAgent:
    def __init__(self, llm_client: LLMClient, max_workers: int = 5):
        self.llm_client = llm_client
        self.max_workers = max_workers


    def _load_audit_questions_from_files(self, project_type: str, attack_surface: str) -> List[Dict[str, Any]]:
        """
        从文件夹加载指定项目类型和攻击面的漏洞类型
        
        Args:
            project_type: 项目类型（python, c, java, go, javascript）
            attack_surface: 攻击面（web, cli, protobuf, blink）
            
        Returns:
            漏洞类型列表
        """
        questions = []
        knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
        vuln_dir = os.path.join(knowledge_dir, project_type, attack_surface)
        
        if os.path.exists(vuln_dir):
            for filename in os.listdir(vuln_dir):
                if filename.endswith('.txt'):
                    filepath = os.path.join(vuln_dir, filename)
                    vuln_type = filename[:-4]  # 移除 .txt 扩展名
                    
                    try:
                        with open(filepath, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            # 第一行是漏洞类型，第二行开始是问题
                            lines = content.split('\n')
                            if len(lines) >= 2:
                                vuln_type = lines[0].strip()
                                question = '\n'.join(lines[1:]).strip()
                                questions.append({
                                    "type": vuln_type,
                                    "question": question
                                })
                    except Exception as e:
                        print(f"读取漏洞文件 {filepath} 失败: {str(e)}")
        
        return questions

    

    def create_audit_tasks(self, functions: List[FunctionInfo], attack_surface: str, project_type: str = None) -> List[AuditTask]:
        """
        创建审计任务
        
        Args:
            functions: 函数列表
            attack_surface: 攻击面
            project_type: 项目类型（可选，如果提供则从文件加载漏洞类型）
            
        Returns:
            审计任务列表
        """
        tasks = []
        
        # 如果提供了项目类型，尝试从文件加载漏洞类型
        if project_type:
            questions = self._load_audit_questions_from_files(project_type, attack_surface)
            if not questions:
                # 如果没有找到文件，报错退出
                print(f"错误: 未找到项目类型为 {project_type} 攻击面为 {attack_surface} 的漏洞类型文件")
                return []
        else:
            # 如果没有找到文件，报错退出
            print(f"错误: 未找到攻击面为 {attack_surface} 的默认漏洞类型文件")
            return []
        
        
        for func in functions:
            for question_info in questions:
                task = AuditTask(
                    task_id=str(uuid.uuid4()),
                    function_info=func,
                    attack_surface=attack_surface,
                    question_type=question_info["type"],
                    question=question_info["question"]
                )
                tasks.append(task)
        
        return tasks

    def create_audit_tasks_with_trace(self, trace_results: List[TraceResult], project_type: str = None) -> List[AuditTask]:
        """
        基于追踪结果创建审计任务
        
        Args:
            trace_results: 追踪结果列表
            project_type: 项目类型（可选，如果提供则从文件加载漏洞类型）
            
        Returns:
            审计任务列表
        """
        tasks = []
        
        if not trace_results:
            return tasks
        
        attack_surface = trace_results[0].attack_surface
        
        # 加载漏洞类型问题
        if project_type:
            questions = self._load_audit_questions_from_files(project_type, attack_surface)
            if not questions:
                print(f"错误: 未找到项目类型为 {project_type} 攻击面为 {attack_surface} 的漏洞类型文件")
                return []
        else:
            print(f"错误: 未找到攻击面为 {attack_surface} 的默认漏洞类型文件")
            return []
        
        # 为每个追踪结果的函数创建审计任务
        for trace_result in trace_results:
            func = trace_result.function_info
            for question_info in questions:
                task = AuditTask(
                    task_id=str(uuid.uuid4()),
                    function_info=func,
                    attack_surface=attack_surface,
                    question_type=question_info["type"],
                    question=question_info["question"]
                )
                tasks.append(task)
        
        return tasks

    def audit_function(self, task: AuditTask, trace_result: Optional[TraceResult] = None) -> AuditResult:
        """
        对单个函数进行审计
        
        Args:
            task: 审计任务
            trace_result: 可选的追踪结果，包含外部输入相关的代码上下文
        """
        system_prompt = """你是一个专业的代码安全审计专家。请仔细分析提供的代码函数，回答关于安全漏洞的问题。

回答格式要求JSON格式，包含以下字段：
{
    "has_vulnerability": true/false,
    "vulnerability_type": "漏洞类型",
    "severity": "严重/高危/中危/低危",
    "description": "漏洞详细描述",
    "evidence": "代码中的具体证据，引用代码片段",
    "suggested_fix": "修复建议",
    "confidence": 0.0-1.0
}

如果没有发现漏洞，has_vulnerability设为false，其他字段可以为null。"""

        user_prompt = f"""审计任务：
攻击面: {task.attack_surface}
漏洞类型: {task.question_type}
审计问题: {task.question}

函数信息：
文件路径: {task.function_info.file_path}
函数名: {task.function_info.function_name}
行号: {task.function_info.line_start}-{task.function_info.line_end}
参数: {', '.join(task.function_info.parameters)}

代码片段:
```
{task.function_info.code_snippet}
```"""

        if trace_result and trace_result.traced_code_contexts:
            user_prompt += f"""

外部输入追踪信息：
数据流摘要: {trace_result.data_flow_summary}

相关代码上下文 ({len(trace_result.traced_code_contexts)} 个):
"""
            for i, ctx in enumerate(trace_result.traced_code_contexts[:10], 1):
                user_prompt += f"""
---
上下文 {i} ({ctx.context_type}):
文件: {ctx.file_path}
行号: {ctx.line_start}-{ctx.line_end}
代码:
```
{ctx.code_snippet}
```
"""

        user_prompt += """

请根据上述信息进行安全审计，返回JSON格式的结果。"""

        try:
            response = self.llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result_dict = self._parse_audit_response(response)
            
            return AuditResult(
                task_id=task.task_id,
                has_vulnerability=result_dict.get("has_vulnerability", False),
                function_info=task.function_info,
                vulnerability_type=result_dict.get("vulnerability_type"),
                severity=result_dict.get("severity"),
                description=result_dict.get("description"),
                evidence=result_dict.get("evidence"),
                suggested_fix=result_dict.get("suggested_fix"),
                confidence=result_dict.get("confidence", 0.0)
            )
        except Exception as e:
            print(f"审计任务 {task.task_id} 失败: {str(e)}")
            return AuditResult(
                task_id=task.task_id,
                has_vulnerability=False,
                function_info=task.function_info,
                confidence=0.0
            )

    def _parse_audit_response(self, response: str) -> Dict[str, Any]:
        """
        解析审计响应
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
            
            return {
                "has_vulnerability": False,
                "confidence": 0.0,
                "raw_response": response
            }

    def audit_functions_concurrent(self, tasks: List[AuditTask], trace_results_map: Optional[Dict[str, TraceResult]] = None) -> List[AuditResult]:
        """
        并发审计多个函数
        
        Args:
            tasks: 审计任务列表
            trace_results_map: 可选的追踪结果映射，key为function_info的标识，value为对应的TraceResult
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_task = {}
            for task in tasks:
                trace_result = None
                if trace_results_map:
                    func_key = f"{task.function_info.file_path}:{task.function_info.function_name}:{task.function_info.line_start}"
                    trace_result = trace_results_map.get(func_key)
                future_to_task[executor.submit(self.audit_function, task, trace_result)] = task
            
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append(result)
                    if result.has_vulnerability:
                        print(f"发现漏洞: {task.function_info.file_path}:{task.function_info.function_name} - {result.vulnerability_type}")
                except Exception as e:
                    print(f"审计任务 {task.task_id} 异常: {str(e)}")
        
        return results

    def get_vulnerabilities_only(self, results: List[AuditResult]) -> List[AuditResult]:
        """
        只返回有漏洞的结果
        """
        return [r for r in results if r.has_vulnerability]
