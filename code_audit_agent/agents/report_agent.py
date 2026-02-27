import os
import json
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from ..utils.models import AuditResult, ExploitResult, VulnerabilityReport
from ..utils.llm_client import LLMClient


class ReportAgent:
    def __init__(self, llm_client: LLMClient, output_dir: Optional[str] = None):
        self.llm_client = llm_client
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成完整的安全审计报告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"security_report_{attack_surface}_{timestamp}.md"
        report_path = os.path.join(self.output_dir, report_filename)
        
        successful_exploits = [r for r in exploit_results if r.exploit_successful]
        
        report_content = self._generate_markdown_report(successful_exploits, code_dir, attack_surface)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"报告已生成: {report_path}")
        return report_path

    def _generate_markdown_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成Markdown格式的报告
        """
        report_lines = []
        
        report_lines.append(f"# 代码安全审计报告")
        report_lines.append(f"\n**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"**审计目录**: {code_dir}")
        report_lines.append(f"**攻击面**: {attack_surface}")
        report_lines.append(f"**发现漏洞数量**: {len(exploit_results)}")
        report_lines.append("\n---\n")
        
        if not exploit_results:
            report_lines.append("## 审计结果")
            report_lines.append("\n未发现可利用的安全漏洞。")
            return "\n".join(report_lines)
        
        report_lines.append("## 目录\n")
        for i, result in enumerate(exploit_results, 1):
            vuln_type = result.audit_result.vulnerability_type or "未知"
            report_lines.append(f"{i}. [{vuln_type}](#{vuln_type.lower().replace(' ', '-')})")
        
        report_lines.append("\n---\n")
        
        for i, result in enumerate(exploit_results, 1):
            report_lines.append(f"## {i}. {result.audit_result.vulnerability_type or '未知漏洞'}")
            report_lines.append(f"\n### 漏洞类型")
            report_lines.append(f"\n{result.audit_result.vulnerability_type}")
            
            report_lines.append(f"\n### 漏洞路径")
            report_lines.append(f"\n**文件**: `{result.audit_result.function_info.file_path}`")
            report_lines.append(f"\n**函数**: `{result.audit_result.function_info.function_name}`")
            
            report_lines.append(f"\n### 漏洞详情")
            report_lines.append(f"\n**严重程度**: {result.audit_result.severity}")
            report_lines.append(f"\n**置信度**: {result.audit_result.confidence:.2f}")
            report_lines.append(f"\n**描述**:\n{result.audit_result.description}")
            
            if result.audit_result.evidence:
                report_lines.append(f"\n**证据**:\n```\n{result.audit_result.evidence}\n```")
            
            if result.audit_result.suggested_fix:
                report_lines.append(f"\n**修复建议**:\n{result.audit_result.suggested_fix}")
            
            report_lines.append(f"\n### 漏洞利用")
            
            if result.exploit_script:
                report_lines.append(f"\n**利用脚本**:\n```python\n{result.exploit_script}\n```")
            
            if result.exploit_output:
                report_lines.append(f"\n**利用输出**:\n```\n{result.exploit_output}\n```")
            
            if result.exploit_screenshot:
                screenshot_rel_path = os.path.relpath(result.exploit_screenshot, self.output_dir)
                report_lines.append(f"\n**利用截图**:\n\n![漏洞利用截图]({screenshot_rel_path})")
            
            cvss_score = self._calculate_cvss_score(result.audit_result)
            report_lines.append(f"\n### CVSS评分")
            report_lines.append(f"\n**CVSS分数**: {cvss_score['score']}")
            report_lines.append(f"\n**CVSS向量**: {cvss_score['vector']}")
            report_lines.append(f"\n**严重等级**: {cvss_score['severity']}")
            
            impact = self._generate_impact_description(result.audit_result)
            report_lines.append(f"\n### 漏洞影响")
            report_lines.append(f"\n{impact}")
            
            report_lines.append("\n---\n")
        
        report_lines.append("## 总结")
        report_lines.append(f"\n本次审计共发现 **{len(exploit_results)}** 个可利用的安全漏洞。")
        
        severity_count = {}
        for result in exploit_results:
            severity = result.audit_result.severity or "未知"
            severity_count[severity] = severity_count.get(severity, 0) + 1
        
        report_lines.append("\n### 漏洞严重程度分布")
        for severity, count in sorted(severity_count.items(), key=lambda x: self._severity_order(x[0])):
            report_lines.append(f"\n- **{severity}**: {count} 个")
        
        report_lines.append("\n### 建议")
        report_lines.append("\n1. 优先修复高严重程度的漏洞")
        report_lines.append("\n2. 对所有漏洞进行验证和测试")
        report_lines.append("\n3. 实施安全编码规范")
        report_lines.append("\n4. 定期进行安全审计")
        report_lines.append("\n5. 建立漏洞管理流程")
        
        return "\n".join(report_lines)

    def _calculate_cvss_score(self, audit_result: AuditResult) -> dict:
        """
        计算CVSS评分
        """
        severity = audit_result.severity or "中危"
        
        severity_mapping = {
            "严重": {"score": 9.0, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H"},
            "高危": {"score": 7.5, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"},
            "中危": {"score": 5.5, "vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N"},
            "低危": {"score": 3.0, "vector": "CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:L/I:N/A:N"}
        }
        
        return severity_mapping.get(severity, {"score": 0.0, "vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N"})

    def _generate_impact_description(self, audit_result: AuditResult) -> str:
        """
        生成漏洞影响描述
        """
        system_prompt = """你是一个安全专家。根据提供的漏洞信息，生成一段详细的漏洞影响描述。

描述应该包括：
1. 漏洞可能造成的直接危害
2. 对业务的影响
3. 对用户的影响
4. 潜在的连锁反应

只返回影响描述文本，不要包含其他内容。"""

        user_prompt = f"""漏洞类型: {audit_result.vulnerability_type}
严重程度: {audit_result.severity}
漏洞描述: {audit_result.description}

请生成详细的漏洞影响描述。"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=messages,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"无法生成影响描述: {str(e)}"

    def _severity_order(self, severity: str) -> int:
        """
        返回严重程度的排序值
        """
        order = {"严重": 0, "高危": 1, "中危": 2, "低危": 3, "未知": 4}
        return order.get(severity, 99)

    def generate_json_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成JSON格式的报告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"security_report_{attack_surface}_{timestamp}.json"
        report_path = os.path.join(self.output_dir, report_filename)
        
        report_data = {
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "code_directory": code_dir,
                "attack_surface": attack_surface,
                "total_vulnerabilities": len(exploit_results)
            },
            "vulnerabilities": []
        }
        
        for result in exploit_results:
            cvss = self._calculate_cvss_score(result.audit_result)
            
            vuln_data = {
                "vulnerability_type": result.audit_result.vulnerability_type,
                "file_path": result.audit_result.function_info.file_path,
                "function_name": result.audit_result.function_info.function_name,
                "line_number": result.audit_result.function_info.line_start,
                "description": result.audit_result.description,
                "severity": result.audit_result.severity,
                "confidence": result.audit_result.confidence,
                "evidence": result.audit_result.evidence,
                "suggested_fix": result.audit_result.suggested_fix,
                "exploit": {
                    "successful": result.exploit_successful,
                    "script": result.exploit_script,
                    "output": result.exploit_output,
                    "screenshot": result.exploit_screenshot
                },
                "cvss": {
                    "score": cvss["score"],
                    "vector": cvss["vector"],
                    "severity": cvss["severity"]
                },
                "impact": self._generate_impact_description(result.audit_result)
            }
            
            report_data["vulnerabilities"].append(vuln_data)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        print(f"JSON报告已生成: {report_path}")
        return report_path

    def generate_html_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成HTML格式的报告
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = f"security_report_{attack_surface}_{timestamp}.html"
        report_path = os.path.join(self.output_dir, report_filename)
        
        html_content = self._generate_html_content(exploit_results, code_dir, attack_surface)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML报告已生成: {report_path}")
        return report_path

    def _generate_html_content(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成HTML内容
        """
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
        .cvss-score {{ font-size: 24px; font-weight: bold; display: inline-block; padding: 10px 20px; border-radius: 5px; color: white; }}
        .cvss-severe {{ background-color: #f44336; }}
        .cvss-high {{ background-color: #ff9800; }}
        .cvss-medium {{ background-color: #ffeb3b; color: #333; }}
        .cvss-low {{ background-color: #4CAF50; }}
        img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 5px; }}
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
            <p><strong>发现漏洞数量</strong>: {len(exploit_results)}</p>
        </div>
"""
        
        if not exploit_results:
            html += """
        <div class="summary">
            <h2>审计结果</h2>
            <p>未发现可利用的安全漏洞。</p>
        </div>
"""
        else:
            for i, result in enumerate(exploit_results, 1):
                cvss = self._calculate_cvss_score(result.audit_result)
                severity_class = self._get_severity_class(result.audit_result.severity)
                cvss_class = self._get_cvss_class(result.audit_result.severity)
                
                html += f"""
        <div class="vulnerability {severity_class}">
            <h2>{i}. {result.audit_result.vulnerability_type or '未知漏洞'}</h2>
            
            <h3>漏洞类型</h3>
            <p>{result.audit_result.vulnerability_type}</p>
            
            <h3>漏洞路径</h3>
            <p><strong>文件</strong>: <code>{result.audit_result.function_info.file_path}</code></p>
            <p><strong>函数</strong>: <code>{result.audit_result.function_info.function_name}</code></p>
            <p><strong>行号</strong>: {result.audit_result.function_info.line_start}-{result.audit_result.function_info.line_end}</p>
            
            <h3>漏洞详情</h3>
            <p><strong>严重程度</strong>: {result.audit_result.severity}</p>
            <p><strong>置信度</strong>: {result.audit_result.confidence:.2f}</p>
            <p><strong>描述</strong>: {result.audit_result.description}</p>
"""
                
                if result.audit_result.evidence:
                    html += f"""
            <p><strong>证据</strong>:</p>
            <pre><code>{result.audit_result.evidence}</code></pre>
"""
                
                if result.audit_result.suggested_fix:
                    html += f"""
            <p><strong>修复建议</strong>: {result.audit_result.suggested_fix}</p>
"""
                
                html += """
            <h3>漏洞利用</h3>
"""
                
                if result.exploit_script:
                    html += f"""
            <p><strong>利用脚本</strong>:</p>
            <pre><code>{result.exploit_script}</code></pre>
"""
                
                if result.exploit_output:
                    html += f"""
            <p><strong>利用输出</strong>:</p>
            <pre><code>{result.exploit_output}</code></pre>
"""
                
                if result.exploit_screenshot:
                    screenshot_rel_path = os.path.relpath(result.exploit_screenshot, self.output_dir)
                    html += f"""
            <p><strong>利用截图</strong>:</p>
            <img src="{screenshot_rel_path}" alt="漏洞利用截图">
"""
                
                html += f"""
            <h3>CVSS评分</h3>
            <p><span class="cvss-score {cvss_class}">{cvss['score']}</span></p>
            <p><strong>CVSS向量</strong>: {cvss['vector']}</p>
            <p><strong>严重等级</strong>: {cvss['severity']}</p>
            
            <h3>漏洞影响</h3>
            <p>{self._generate_impact_description(result.audit_result)}</p>
        </div>
"""
            
            html += f"""
        <div class="summary">
            <h2>总结</h2>
            <p>本次审计共发现 <strong>{len(exploit_results)}</strong> 个可利用的安全漏洞。</p>
            
            <h3>漏洞严重程度分布</h3>
"""
            
            severity_count = {}
            for result in exploit_results:
                severity = result.audit_result.severity or "未知"
                severity_count[severity] = severity_count.get(severity, 0) + 1
            
            for severity, count in sorted(severity_count.items(), key=lambda x: self._severity_order(x[0])):
                html += f"""
            <p>- <strong>{severity}</strong>: {count} 个</p>
"""
            
            html += """
            <h3>建议</h3>
            <ol>
                <li>优先修复高严重程度的漏洞</li>
                <li>对所有漏洞进行验证和测试</li>
                <li>实施安全编码规范</li>
                <li>定期进行安全审计</li>
                <li>建立漏洞管理流程</li>
            </ol>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html

    def _get_severity_class(self, severity: Optional[str]) -> str:
        """
        获取严重程度对应的CSS类
        """
        mapping = {
            "严重": "severe",
            "高危": "high",
            "中危": "medium",
            "低危": "low"
        }
        return mapping.get(severity, "")

    def _get_cvss_class(self, severity: Optional[str]) -> str:
        """
        获取CVSS评分对应的CSS类
        """
        mapping = {
            "严重": "cvss-severe",
            "高危": "cvss-high",
            "中危": "cvss-medium",
            "低危": "cvss-low"
        }
        return mapping.get(severity, "")
