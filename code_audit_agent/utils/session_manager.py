import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from code_audit_agent.utils.models import (
    AuditResult, CodeContext, ExploitResult, FunctionInfo, TraceResult
)


class SessionManager:
    STAGES = ['scanner', 'trace', 'audit', 'exploit', 'report']
    SESSIONS_DIR = 'code_audit_agent/sessions'

    def __init__(self, session_id: str, session_dir: str = None):
        self.session_id = session_id
        self.session_dir = session_dir or os.path.join(
            os.path.dirname(__file__), '..', '..', self.SESSIONS_DIR, session_id
        )

    @classmethod
    def create(cls, project_type: str, attack_surface: str, code_dir: str, 
               docker_image: Optional[str] = None, container_id: Optional[str] = None) -> 'SessionManager':
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_id = f"{timestamp}_{project_type}_{attack_surface}"
        instance = cls(session_id)
        os.makedirs(instance.session_dir, exist_ok=True)

        metadata = {
            'session_id': session_id,
            'project_type': project_type,
            'attack_surface': attack_surface,
            'code_dir': os.path.abspath(code_dir),
            'created_at': datetime.now().isoformat(),
            'completed_stages': [],
            'docker_image': docker_image,
            'container_id': container_id
        }
        instance._save_metadata(metadata)
        return instance

    @classmethod
    def load(cls, session_id: str) -> Optional['SessionManager']:
        instance = cls(session_id)
        if os.path.exists(instance.session_dir):
            return instance
        return None

    @classmethod
    def list_sessions(cls) -> List[Dict[str, Any]]:
        sessions_dir = os.path.join(os.path.dirname(__file__), '..', '..', cls.SESSIONS_DIR)
        if not os.path.exists(sessions_dir):
            return []

        sessions = []
        for session_id in os.listdir(sessions_dir):
            session_path = os.path.join(sessions_dir, session_id)
            if os.path.isdir(session_path):
                metadata_path = os.path.join(session_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    metadata['session_id'] = session_id
                    sessions.append(metadata)
                else:
                    sessions.append({
                        'session_id': session_id,
                        'created_at': 'unknown'
                    })

        sessions.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return sessions

    def get_stage_file(self, stage: str) -> str:
        return os.path.join(self.session_dir, f'{stage}.json')

    def save(self, stage: str, data: Any) -> str:
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        filepath = self.get_stage_file(stage)
        serializable_data = self._serialize(data)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable_data, f, ensure_ascii=False, indent=2)

        self._update_completed_stages(stage)
        return filepath

    def load_data(self, stage: str) -> Optional[Any]:
        if stage not in self.STAGES:
            raise ValueError(f"Invalid stage: {stage}")

        filepath = self.get_stage_file(stage)
        if not os.path.exists(filepath):
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return self._deserialize(stage, data)

    def has_results(self, stage: str) -> bool:
        filepath = self.get_stage_file(stage)
        return os.path.exists(filepath)

    def get_latest_completed_stage(self) -> Optional[str]:
        metadata = self._load_metadata()
        completed = metadata.get('completed_stages', [])
        if not completed:
            return None
        for stage in reversed(self.STAGES):
            if stage in completed:
                return stage
        return None

    def get_next_stage(self) -> str:
        latest = self.get_latest_completed_stage()
        if latest is None:
            return self.STAGES[0]
        idx = self.STAGES.index(latest)
        if idx + 1 < len(self.STAGES):
            return self.STAGES[idx + 1]
        return self.STAGES[-1]

    def _serialize(self, data: Any) -> Any:
        if isinstance(data, list):
            return [self._serialize(item) for item in data]
        elif isinstance(data, dict):
            return {key: self._serialize(value) for key, value in data.items()}
        elif is_dataclass(data):
            return asdict(data)
        elif hasattr(data, '__dict__'):
            return asdict(data)
        return data

    def _deserialize(self, stage: str, data: Any) -> Any:
        if stage == 'scanner':
            return self._deserialize_functions(data)
        elif stage == 'trace':
            return self._deserialize_trace_results(data)
        elif stage == 'audit':
            return self._deserialize_audit_results(data)
        elif stage == 'exploit':
            return self._deserialize_exploit_results(data)
        return data

    def _deserialize_functions(self, data: List[Dict]) -> List[FunctionInfo]:
        return [
            FunctionInfo(
                file_path=item['file_path'],
                function_name=item['function_name'],
                code_snippet=item.get('code_snippet', '')
            )
            for item in data
        ]

    def _deserialize_trace_results(self, data: List[Dict]) -> List[TraceResult]:
        results = []
        for item in data:
            function_info = FunctionInfo(
                file_path=item['function_info']['file_path'],
                function_name=item['function_info']['function_name'],
                code_snippet=item['function_info'].get('code_snippet', '')
            )
            code_map = [
                CodeContext(
                    file_path=ctx['file_path'],
                    line_start=ctx['line_start'],
                    line_end=ctx['line_end'],
                    code_snippet=ctx.get('code_snippet', ''),
                    context_type=ctx.get('context_type', 'function')
                )
                for ctx in item.get('code_map', [])
            ]
            trace_result = TraceResult(
                task_id=item['task_id'],
                function_info=function_info,
                attack_surface=item['attack_surface'],
                project_type=item['project_type'],
                code_logic=item.get('code_logic', ''),
                trace_complete=item.get('trace_complete', True),
                error_message=item.get('error_message'),
                full_msg=item.get('full_msg'),
                code_map=code_map
            )
            results.append(trace_result)
        return results

    def _deserialize_audit_results(self, data: List[Dict]) -> List[AuditResult]:
        results = []
        for item in data:
            function_info = FunctionInfo(
                file_path=item['function_info']['file_path'],
                function_name=item['function_info']['function_name'],
                code_snippet=item['function_info'].get('code_snippet', '')
            )

            trace_data = item.get('trace_result')
            if trace_data:
                trace_function_info = FunctionInfo(
                    file_path=trace_data['function_info']['file_path'],
                    function_name=trace_data['function_info']['function_name'],
                    code_snippet=trace_data['function_info'].get('code_snippet', '')
                )
                trace_code_map = [
                    CodeContext(
                        file_path=ctx['file_path'],
                        line_start=ctx['line_start'],
                        line_end=ctx['line_end'],
                        code_snippet=ctx.get('code_snippet', ''),
                        context_type=ctx.get('context_type', 'function')
                    )
                    for ctx in trace_data.get('code_map', [])
                ]
                trace_result = TraceResult(
                    task_id=trace_data['task_id'],
                    function_info=trace_function_info,
                    attack_surface=trace_data['attack_surface'],
                    project_type=trace_data['project_type'],
                    code_logic=trace_data.get('code_logic', ''),
                    trace_complete=trace_data.get('trace_complete', True),
                    error_message=trace_data.get('error_message'),
                    full_msg=trace_data.get('full_msg'),
                    code_map=trace_code_map
                )
            else:
                trace_result = None

            audit_result = AuditResult(
                task_id=item['task_id'],
                has_vulnerability=item['has_vulnerability'],
                function_info=function_info,
                trace_result=trace_result,
                vulnerability_type=item.get('vulnerability_type'),
                severity=item.get('severity'),
                description=item.get('description'),
                evidence=item.get('evidence'),
                suggested_fix=item.get('suggested_fix'),
                confidence=item.get('confidence', 0.0)
            )
            results.append(audit_result)
        return results

    def _deserialize_exploit_results(self, data: List[Dict]) -> List[ExploitResult]:
        results = []
        for item in data:
            audit_data = item.get('audit_result')
            if audit_data:
                function_info = FunctionInfo(
                    file_path=audit_data['function_info']['file_path'],
                    function_name=audit_data['function_info']['function_name'],
                    code_snippet=audit_data['function_info'].get('code_snippet', '')
                )

                trace_data = audit_data.get('trace_result')
                if trace_data:
                    trace_function_info = FunctionInfo(
                        file_path=trace_data['function_info']['file_path'],
                        function_name=trace_data['function_info']['function_name'],
                        code_snippet=trace_data['function_info'].get('code_snippet', '')
                    )
                    trace_code_map = [
                        CodeContext(
                            file_path=ctx['file_path'],
                            line_start=ctx['line_start'],
                            line_end=ctx['line_end'],
                            code_snippet=ctx.get('code_snippet', ''),
                            context_type=ctx.get('context_type', 'function')
                        )
                        for ctx in trace_data.get('code_map', [])
                    ]
                    trace_result = TraceResult(
                        task_id=trace_data['task_id'],
                        function_info=trace_function_info,
                        attack_surface=trace_data['attack_surface'],
                        project_type=trace_data['project_type'],
                        code_logic=trace_data.get('code_logic', ''),
                        trace_complete=trace_data.get('trace_complete', True),
                        error_message=trace_data.get('error_message'),
                        full_msg=trace_data.get('full_msg'),
                        code_map=trace_code_map
                    )
                else:
                    trace_result = None

                audit_result = AuditResult(
                    task_id=audit_data['task_id'],
                    has_vulnerability=audit_data['has_vulnerability'],
                    function_info=function_info,
                    trace_result=trace_result,
                    vulnerability_type=audit_data.get('vulnerability_type'),
                    severity=audit_data.get('severity'),
                    description=audit_data.get('description'),
                    evidence=audit_data.get('evidence'),
                    suggested_fix=audit_data.get('suggested_fix'),
                    confidence=audit_data.get('confidence', 0.0)
                )
            else:
                audit_result = None

            exploit_result = ExploitResult(
                audit_result=audit_result,
                exploit_successful=item.get('exploit_successful', False),
                exploit_script=item.get('exploit_script'),
                exploit_output=item.get('exploit_output'),
                exploit_screenshot=item.get('exploit_screenshot'),
                error_message=item.get('error_message')
            )
            results.append(exploit_result)
        return results

    def _save_metadata(self, metadata: Dict):
        filepath = os.path.join(self.session_dir, 'metadata.json')
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def _load_metadata(self) -> Dict:
        filepath = os.path.join(self.session_dir, 'metadata.json')
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _update_completed_stages(self, completed_stage: str):
        metadata = self._load_metadata()
        completed_stages = metadata.get('completed_stages', [])

        for stage in self.STAGES:
            if stage == completed_stage:
                if stage not in completed_stages:
                    completed_stages.append(stage)
                break
            if stage not in completed_stages:
                break

        metadata['completed_stages'] = completed_stages
        metadata['last_updated'] = datetime.now().isoformat()
        self._save_metadata(metadata)

    def update_docker_info(self, docker_image: str, container_id: str):
        metadata = self._load_metadata()
        metadata['docker_image'] = docker_image
        metadata['container_id'] = container_id
        metadata['last_updated'] = datetime.now().isoformat()
        self._save_metadata(metadata)

    def get_docker_info(self) -> Dict[str, Optional[str]]:
        metadata = self._load_metadata()
        return {
            'docker_image': metadata.get('docker_image'),
            'container_id': metadata.get('container_id')
        }

    def get_code_dir(self) -> str:
        metadata = self._load_metadata()
        return metadata.get('code_dir', '')
