import os
from typing import List, Optional
from datetime import datetime

from ..utils.models import ExploitResult
from ..utils.llm_client import LLMClient


class ReportAgent:
    def __init__(self, llm_client: LLMClient, output_dir: Optional[str] = None):
        self.llm_client = llm_client
        self.output_dir = output_dir or os.path.join(os.path.dirname(__file__), "..", "reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        生成完整的安全审计报告（Markdown格式）
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
        生成Markdown格式的报告（使用大模型生成，包含CVSS评分）
        """
        if not exploit_results:
            return f"""# 代码安全审计报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**审计目录**: {code_dir}
**攻击面**: {attack_surface}
**发现漏洞数量**: 0

---

## 审计结果

未发现可利用的安全漏洞。
"""
        
        return self._generate_llm_report(exploit_results, code_dir, attack_surface)

    def _generate_llm_report(self, exploit_results: List[ExploitResult], code_dir: str, attack_surface: str) -> str:
        """
        使用大模型生成Markdown格式的报告（包含CVSS评分）
        """
        system_prompt = """你是一个专业的安全审计报告撰写专家。请根据提供的漏洞信息，生成符合以下格式的markdown安全审计报告。

报告格式要求：

# 【严重程度】【被测程序】【漏洞模块/攻击面】xxx函数存在xx漏洞

## 漏洞信息
这里包括漏洞代码点和具体数据流

## poc脚本/命令

## 利用效果

---

**严重程度分类**（根据CVSS评分自动判断）：
- 一般：CVSS 0.0-3.9
- 严重：CVSS 4.0-6.9
- 致命：CVSS 7.0-10.0

**CVSS v3.1评分标准**：

**基础指标 (Base Metrics):**

1. 攻击向量 (Attack Vector - AV):
   - Network (N): 可通过网络远程利用
   - Adjacent (A): 需要本地网络或物理相邻
   - Local (L): 需要本地访问
   - Physical (P): 需要物理接触

2. 攻击复杂度 (Attack Complexity - AC):
   - Low (L): 攻击复杂度低，容易利用
   - High (H): 攻击复杂度高，难以利用

3. 所需权限 (Privileges Required - PR):
   - None (N): 不需要任何权限
   - Low (L): 需要低权限（如普通用户）
   - High (H): 需要高权限（如管理员）

4. 用户交互 (User Interaction - UI):
   - None (N): 不需要用户交互
   - Required (R): 需要用户交互

5. 影响范围 (Scope - S):
   - Unchanged (U): 影响范围不变
   - Changed (C): 影响范围改变（影响其他组件）

6. 机密性影响 (Confidentiality - C):
   - High (H): 完全泄露敏感信息
   - Low (L): 部分泄露敏感信息
   - None (N): 无影响

7. 完整性影响 (Integrity - I):
   - High (H): 完全破坏数据完整性
   - Low (L): 部分破坏数据完整性
   - None (N): 无影响

8. 可用性影响 (Availability - A):
   - High (H): 完全破坏服务可用性
   - Low (L): 部分影响服务可用性
   - None (N): 无影响

**CVSS向量格式:**
CVSS:3.1/AV:[N|A|L|P]/AC:[L|H]/PR:[N|L|H]/UI:[N|R]/S:[U|C]/C:[H|L|N]/I:[H|L|N]/A:[H|L|N]

**注意事项**：
1. 严重程度要根据CVSS评分自动判断
2. 漏洞信息要详细描述漏洞代码位置、数据流、触发条件
3. POC脚本/命令要完整可执行
4. 利用效果要描述实际利用后的结果
5. 每个漏洞之间用 --- 分隔
6. 使用markdown格式，代码块使用 ``` 标记
7. 只返回报告内容，不要包含其他说明文字"""

        vulnerability_list = []
        for i, result in enumerate(exploit_results, 1):
            vuln_info = f"""
漏洞 #{i}:
- 漏洞类型: {result.audit_result.vulnerability_type or '未知'}
- 原始严重程度: {result.audit_result.severity}
- 置信度: {result.audit_result.confidence:.2f}
- 漏洞描述: {result.audit_result.description or '无描述'}
- 漏洞证据: {result.audit_result.evidence or '无证据'}
- 修复建议: {result.audit_result.suggested_fix or '无建议'}
- 文件路径: {result.audit_result.function_info.file_path}
- 函数名: {result.audit_result.function_info.function_name}
- 代码片段: 
```
{result.audit_result.function_info.code_snippet or '无代码片段'}
```
- 利用脚本: {result.exploit_script or '无利用脚本'}
- 利用输出: {result.exploit_output or '无利用输出'}
- 利用截图: {result.exploit_screenshot or '无截图'}
"""
            vulnerability_list.append(vuln_info)

        user_prompt = f"""请根据以下漏洞信息生成安全审计报告，并为每个漏洞计算CVSS 3.1评分：

**审计信息**：
- 审计目录: {code_dir}
- 攻击面: {attack_surface}
- 发现漏洞数量: {len(exploit_results)}
- 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**漏洞详情**：
{''.join(vulnerability_list)}

请按照指定格式生成完整的markdown报告，并在每个漏洞的"漏洞信息"部分包含：
- 漏洞类型
- 文件路径
- 函数名
- 行号
- CVSS评分（分数、向量、严重等级）
- 漏洞描述
- 漏洞证据
- 漏洞代码点（数据流分析）"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=messages,
                temperature=0.3,
            )
            report_content = response.choices[0].message.content.strip()
            
            return report_content
            
        except Exception as e:
            raise Exception(f"大模型生成报告失败: {str(e)}")
