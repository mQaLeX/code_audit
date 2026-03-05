import argparse
import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv


def _find_dotenv() -> Optional[Path]:
    start_dir = Path.cwd()
    for parent in [start_dir] + list(start_dir.parents):
        env_path = parent / '.env'
        if env_path.exists():
            return env_path
    return None


_env_loaded = False
_dotenv_path = _find_dotenv()
if _dotenv_path:
    load_dotenv(_dotenv_path, override=True)
    _env_loaded = True


class Config:
    _instance: Optional['Config'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._parse_arguments()

    def _get_knowledge_base_dir(self) -> str:
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'code_audit_agent', 'knowledge')

    def _get_project_types(self) -> List[str]:
        knowledge_dir = self._get_knowledge_base_dir()
        project_types = []
        
        if os.path.exists(knowledge_dir):
            for item in os.listdir(knowledge_dir):
                if os.path.isdir(os.path.join(knowledge_dir, item)):
                    project_types.append(item)
        
        return sorted(project_types)

    def _get_attack_surfaces(self, project_type: str) -> List[str]:
        knowledge_dir = self._get_knowledge_base_dir()
        project_dir = os.path.join(knowledge_dir, project_type)
        
        attack_surfaces = []
        
        if os.path.exists(project_dir):
            for item in os.listdir(project_dir):
                if os.path.isdir(os.path.join(project_dir, item)):
                    attack_surfaces.append(item)
        
        return sorted(attack_surfaces)

    def _parse_arguments(self):
        project_types = self._get_project_types()
        all_attack_surfaces = set()
        for pt in project_types:
            all_attack_surfaces.update(self._get_attack_surfaces(pt))
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
        
        parser.add_argument(
            '--audit',
            help='使用历史审计结果："list"显示历史记录，或指定文件名直接使用该审计结果进行后续步骤（漏洞利用和报告生成）'
        )
        
        parser.add_argument(
            '--exploit',
            help='使用历史漏洞利用结果："list"显示历史记录，或指定文件名直接使用该利用结果进行报告生成'
        )
        
        parser.add_argument(
            '--list',
            choices=['sessions', 'trace', 'audit', 'exploit'],
            help='列出历史会话或结果文件: sessions-历史会话, trace-追踪结果, audit-审计结果, exploit-利用结果'
        )
        
        parser.add_argument(
            '--session',
            help='指定会话ID来恢复历史会话（查看: python main.py --list sessions)'
        )
        
        parser.add_argument(
            '--from-stage',
            choices=['scanner', 'trace', 'audit', 'exploit', 'report'],
            help='从指定阶段开始执行（跳过前面阶段）'
        )
        
        args = parser.parse_args()
        
        self.project_type = args.project_type
        self.attack_surface = args.attack_surface
        self.code_dir = args.code_dir
        self.api_key = args.api_key or os.getenv('OPENAI_API_KEY')
        self.base_url = args.base_url or os.getenv('OPENAI_BASE_URL')
        self.model = args.model or os.getenv('OPENAI_MODEL') or os.getenv('DEFAULT_MODEL')
        self.max_workers = args.max_workers
        self.output_dir = args.output_dir
        self.skip_exploit = args.skip_exploit
        self.verbose = args.verbose
        self.debug = args.debug
        self.enable_lsp = args.enable_lsp
        self.lsp_command = args.lsp_command
        self.trace = args.trace
        self.audit = args.audit
        self.exploit = args.exploit
        self.session_id = args.session
        self.from_stage = args.from_stage
        self.list_type = args.list or getattr(args, 'list_type', None)
        self.raw_args = args
        self.env_loaded = _env_loaded
        self.dotenv_path = str(_dotenv_path) if _dotenv_path else None


def get_config() -> Config:
    return Config()
