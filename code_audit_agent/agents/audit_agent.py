import json
import os
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import uuid
from rich.console import Console
from ..utils.models import (
    AuditTask,
    AuditResult,
    FunctionInfo,
    TraceResult,
    CodeContext
)
from ..utils.llm_client import LLMClient
from ..utils.code_environment import CodeEnvironment
import traceback
console = Console()



class AuditAgent:
    def __init__(self, llm_client: LLMClient, max_workers: int = 5, attack_surface: str = "", project_type: str = "", debug: bool = False, code_dir: str = ""):
        self.llm_client = llm_client
        self.max_workers = max_workers
        self.attack_surface = attack_surface
        self.project_type = project_type
        self.debug = debug
        self.code_dir = code_dir
        self.code_environment = CodeEnvironment(code_dir)



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

    def create_audit_tasks_with_trace(self, trace_results: List[TraceResult]) -> List[AuditTask]:
        """
        基于追踪结果创建审计任务
        
        Args:
            trace_results: 追踪结果列表
            
        Returns:
            审计任务列表
        """
        tasks = []
        
        if not trace_results:
            return tasks
        
        
        # 加载漏洞类型问题
        if self.project_type:
            questions = self._load_audit_questions_from_files(self.project_type, self.attack_surface)
            console.print(f"[green]加载了 {len(questions)} 个漏洞类型问题[/green]")
            if not questions:
                print(f"错误: 未找到项目类型为 {self.project_type} 攻击面为 {self.attack_surface} 的漏洞类型文件")
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
                    attack_surface=self.attack_surface,
                    question_type=question_info["type"],
                    question=question_info["question"]
                )
                tasks.append(task)
        
        return tasks

    def _debug_print(self, message: str):
        """调试信息打印"""
        if self.debug:
            console.print(f"[dim][DEBUG] {message}[/dim]")

    def _build_initial_messages(self, task: AuditTask, trace_result: Optional[TraceResult] = None) -> List[Dict[str, Any]]:
        """构建初始消息列表"""
        system_prompt = """你是一个专业的代码安全审计专家。请仔细分析提供的代码函数，回答关于安全漏洞的问题。

你可以使用 ACI 工具来获取更多代码上下文。工具使用格式为在独立的一行中输出命令。

可用工具：
{tools_prompt}

重要：
1. 在完成漏洞判断之前，你可以使用工具来获取更多上下文
2. 当你有足够信息判断是否存在漏洞时，使用 `submit` 命令提交结果
3. 提交结果必须包含完整的审计结论，不要在提交后继续分析


如果没有发现漏洞，has_vulnerability设为false，其他字段可以为null。"""

        if self.code_environment:
            tools_prompt = self.code_environment.get_tools_prompt()
        else:
            tools_prompt = "无可用工具"

        system_prompt = system_prompt.format(tools_prompt=tools_prompt)

        user_prompt = f"""审计任务：
攻击面: {task.attack_surface}
漏洞类型: {task.question_type}
审计问题: {task.question}

函数信息：
文件路径: {task.function_info.file_path}
函数名: {task.function_info.function_name}

代码片段:
```
{task.function_info.code_snippet}
```"""

        if trace_result and trace_result.code_map:
            user_prompt += f"""

外部输入追踪信息：
数据流摘要: {trace_result.code_logic}

相关代码上下文 ({len(trace_result.code_map)} 个):
"""
            for i, ctx in enumerate(trace_result.code_map):
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

请开始审计。并响应下一步行动，你应该输出命令。"""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

    def _execute_aci_command(self, command: str) -> str:
        """执行 ACI 命令并返回结果"""
        if not self.code_environment:
            return "错误: CodeEnvironment 未初始化"

        self._debug_print(f"执行 ACI 命令: {command}")

        result = self.code_environment.execute(command)

        if result.get("error"):
            return f"错误: {result.get('error')}"

        return result.get("output", "")

    def _is_submit_command(self, message: str) -> bool:
        """检查消息是否包含 submit 命令"""
        return "submit" in message.strip().lower().split() and message.strip().lower().startswith("submit")

    def _generate_audit_result(self, messages: List[Dict[str, Any]], task: AuditTask) -> Dict[str, Any]:
        """在检测到 submit 后，单独调用 LLM 生成审计结果"""
        result_prompt = """请根据之前的对话上下文，生成最终的审计结果。

返回JSON格式，包含以下字段：
{
    "has_vulnerability": true/false,
    "vulnerability_type": "漏洞类型",
    "severity": "严重/高危/中危/低危",
    "description": "漏洞详细描述",
    "evidence": "代码中的具体证据，引用代码片段",
    "suggested_fix": "修复建议",
    "confidence": 0.0-1.0
}

如果没有发现漏洞，has_vulnerability设为false，其他字段可以为null。

只返回JSON，不要包含其他内容。"""

        result_messages = messages + [{"role": "user", "content": result_prompt}]

        self._debug_print("调用 LLM 生成最终审计结果")

        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=result_messages,
                temperature=0,
            )
            response_content = response.choices[0].message.content

            self._debug_print(f"审计结果响应长度: {len(response_content)} 字符")

            return self._parse_audit_response(response_content)
        except Exception as e:
            self._debug_print(f"生成审计结果失败: {str(e)}")
            return {
                "has_vulnerability": False,
                "confidence": 0.0
            }

    def audit_function(self, task: AuditTask, trace_result: Optional[TraceResult] = None) -> AuditResult:
        """
        对单个函数进行多轮对话审计

        Args:
            task: 审计任务
            trace_result: 可选的追踪结果，包含外部输入相关的代码上下文

        Returns:
            AuditResult: 审计结果
        """
        max_turns = 10
        current_turn = 0

        messages = self._build_initial_messages(task, trace_result)

        self._debug_print(f"开始审计任务 {task.task_id}: {task.function_info.function_name}")

        try:
            while current_turn < max_turns:
                current_turn += 1
                self._debug_print(f"第 {current_turn} 轮对话")

                response = self.llm_client.client.chat.completions.create(
                    model=self.llm_client.model,
                    messages=messages,
                    temperature=0,
                )
                response_content = response.choices[0].message.content

                self._debug_print(f"LLM 响应长度: {len(response_content)} 字符")

                if self._is_submit_command(response_content):
                    self._debug_print("检测到 submit 命令，生成审计结果")

                    result_dict = self._generate_audit_result(messages, task)

                    return AuditResult(
                        task_id=task.task_id,
                        has_vulnerability=result_dict.get("has_vulnerability", False),
                        function_info=task.function_info,
                        trace_result=trace_result,
                        vulnerability_type=result_dict.get("vulnerability_type"),
                        severity=result_dict.get("severity"),
                        description=result_dict.get("description"),
                        evidence=result_dict.get("evidence"),
                        suggested_fix=result_dict.get("suggested_fix"),
                        confidence=result_dict.get("confidence", 0.0)
                    )

                messages.append({"role": "assistant", "content": response_content})

                command_lines = response_content.strip().split('\n')
                tool_responses = []

                for line in command_lines:
                    line = line.strip()
                    if line and (line.startswith("open ") or line.startswith("go_to_def ") or
                                 line.startswith("find_refs ") or line.startswith("search ") or
                                 line.startswith("search_file ") or line == "view"):
                        self._debug_print(f"执行工具命令: {line}")
                        tool_result = self._execute_aci_command(line)
                        tool_responses.append(f"命令: {line}\n结果:\n{tool_result}")

                if tool_responses:
                    messages.append({
                        "role": "user",
                        "content": "工具执行结果:\n\n" + "\n\n".join(tool_responses)
                    })
                    self._debug_print(f"添加了 {len(tool_responses)} 个工具响应到对话中")
                else:
                    if current_turn >= 3:
                        self._debug_print("多轮对话已达最大轮次，强制提交空结果")
                        break

            self._debug_print("达到最大轮次或无法判断漏洞，返回无漏洞结果")
            return AuditResult(
                task_id=task.task_id,
                has_vulnerability=False,
                function_info=task.function_info,
                trace_result=trace_result,
                confidence=0.0
            )

        except Exception as e:
            self._debug_print(f"审计异常: {str(e)}")
            traceback.print_exc()
            return AuditResult(
                task_id=task.task_id,
                has_vulnerability=False,
                function_info=task.function_info,
                trace_result=trace_result,
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
                    func_key = f"{task.function_info.file_path}:{task.function_info.function_name}"
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
                    traceback.print_exc()
                    console.print(f"[bold red]审计任务 {task.task_id} 异常: {str(e)}[/bold red]")
        
        return results

    def get_vulnerabilities_only(self, results: List[AuditResult]) -> List[AuditResult]:
        """
        只返回有漏洞的结果
        """
        return [r for r in results if r.has_vulnerability]

    def save_audit_results(self, results: List[AuditResult], attack_surface: str) -> str:
        """
        保存审计结果到 JSON 文件
        """
        import json
        from datetime import datetime
        
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_results_{attack_surface}_{timestamp}.json"
        filepath = os.path.join(reports_dir, filename)
        
        data = {
            "timestamp": timestamp,
            "attack_surface": attack_surface,
            "total_results": len(results),
            "vulnerabilities": [self._audit_result_to_dict(r) for r in results]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"审计结果已保存: {filepath}")
        return filepath

    def load_audit_results(self, filepath: str) -> List[AuditResult]:
        """
        从 JSON 文件加载审计结果
        """
        import json
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        results = []
        for vuln_data in data.get("vulnerabilities", []):
            result = self._dict_to_audit_result(vuln_data)
            results.append(result)
        
        return results

    def _audit_result_to_dict(self, result: AuditResult) -> dict:
        """
        将 AuditResult 转换为字典
        """
        return {
            "task_id": result.task_id,
            "has_vulnerability": result.has_vulnerability,
            "vulnerability_type": result.vulnerability_type,
            "severity": result.severity,
            "description": result.description,
            "evidence": result.evidence,
            "suggested_fix": result.suggested_fix,
            "confidence": result.confidence,
            "function_info": {
                "file_path": result.function_info.file_path,
                "function_name": result.function_info.function_name,
                "code_snippet": result.function_info.code_snippet,
            } if result.function_info else None,
            "trace_result": {
                "code_logic": result.trace_result.code_logic if result.trace_result else None,
                "code_map": [
                    {
                        "file_path": cm.file_path,
                        "line_start": cm.line_start,
                        "line_end": cm.line_end,
                        "code_snippet": cm.code_snippet,
                        "context_type": cm.context_type
                    }
                    for cm in result.trace_result.code_map
                ] if result.trace_result and result.trace_result.code_map else []
            } if result.trace_result else None
        }

    def _dict_to_audit_result(self, data: dict) -> AuditResult:
        """
        将字典转换为 AuditResult
        """
        from ..utils.models import FunctionInfo, TraceResult, CodeContext
        
        func_info_data = data.get("function_info", {})
        function_info = FunctionInfo(
            file_path=func_info_data.get("file_path", ""),
            function_name=func_info_data.get("function_name", ""),
            line_start=func_info_data.get("line_start", 0),
            line_end=func_info_data.get("line_end", 0),
            code_snippet=func_info_data.get("code_snippet", "")
        )
        
        trace_result_data = data.get("trace_result", {})
        code_map = []
        for cm_data in trace_result_data.get("code_map", []):
            code_map.append(CodeContext(
                file_path=cm_data.get("file_path", ""),
                line_start=cm_data.get("line_start", 0),
                line_end=cm_data.get("line_end", 0),
                code_snippet=cm_data.get("code_snippet", ""),
                context_type=cm_data.get("context_type", "function")
            ))
        
        trace_result = TraceResult(
            task_id=data.get("task_id", ""),
            function_info=function_info,
            attack_surface="",
            project_type="",
            code_logic=trace_result_data.get("code_logic", ""),
            trace_complete=True,
            error_message=None,
            code_map=code_map,
            full_msg=""
        )
        
        return AuditResult(
            task_id=data.get("task_id", ""),
            has_vulnerability=data.get("has_vulnerability", False),
            function_info=function_info,
            trace_result=trace_result,
            vulnerability_type=data.get("vulnerability_type"),
            severity=data.get("severity"),
            description=data.get("description"),
            evidence=data.get("evidence"),
            suggested_fix=data.get("suggested_fix"),
            confidence=data.get("confidence", 0.0)
        )

    def generate_audit_html_report(self, results: List[AuditResult], attack_surface: str, code_dir: str) -> str:
        """
        生成审计结果的 HTML 报告
        """
        from datetime import datetime
        
        reports_dir = os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"audit_report_{attack_surface}_{timestamp}.html"
        filepath = os.path.join(reports_dir, filename)
        
        vulnerabilities = [r for r in results if r.has_vulnerability]
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>代码安全审计报告 - {attack_surface}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 0; padding: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; border-bottom: 2px solid #ddd; padding-bottom: 5px; margin-top: 30px; }}
        h3 {{ color: #666; }}
        .metadata {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .vulnerability {{ border: 1px solid #ddd; border-radius: 5px; padding: 20px; margin-bottom: 20px; }}
        .vulnerability.severe {{ border-left: 5px solid #f44336; }}
        .vulnerability.high {{ border-left: 5px solid #ff9800; }}
        .vulnerability.medium {{ border-left: 5px solid #ffeb3b; }}
        .vulnerability.low {{ border-left: 5px solid #4CAF50; }}
        pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
        code {{ background-color: #f5f5f5; padding: 2px 5px; border-radius: 3px; }}
        .summary {{ background-color: #e3f2fd; padding: 20px; border-radius: 5px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>代码安全审计报告</h1>
        
        <div class="metadata">
            <p><strong>生成时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p><strong>审计目录</strong>: {code_dir}</p>
            <p><strong>攻击面</strong>: {attack_surface}</p>
            <p><strong>审计函数总数</strong>: {len(results)}</p>
            <p><strong>发现漏洞数量</strong>: {len(vulnerabilities)}</p>
        </div>
"""
        
        if not vulnerabilities:
            html += """
        <div class="summary">
            <h2>审计结果</h2>
            <p>未发现安全漏洞。</p>
        </div>
"""
        else:
            for i, result in enumerate(vulnerabilities, 1):
                severity_class = {
                    "Critical": "severe",
                    "High": "high", 
                    "Medium": "medium",
                    "Low": "low"
                }.get(result.severity, "medium")
                
                html += f"""
        <div class="vulnerability {severity_class}">
            <h2>{i}. {result.vulnerability_type or '未知漏洞'}</h2>
            
            <h3>漏洞路径</h3>
            <p><strong>文件</strong>: <code>{result.function_info.file_path}</code></p>
            <p><strong>函数</strong>: <code>{result.function_info.function_name}</code></p>
            
            <h3>漏洞详情</h3>
            <p><strong>严重程度</strong>: {result.severity}</p>
            <p><strong>置信度</strong>: {result.confidence:.2f}</p>
            <p><strong>描述</strong>: {result.description}</p>
"""
                if result.evidence:
                    html += f"""
            <p><strong>证据</strong>:</p>
            <pre><code>{result.evidence}</code></pre>
"""
                if result.suggested_fix:
                    html += f"""
            <p><strong>建议修复</strong>:</p>
            <pre><code>{result.suggested_fix}</code></pre>
"""
                html += """
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"HTML报告已生成: {filepath}")
        return filepath
