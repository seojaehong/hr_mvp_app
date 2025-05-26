"""
정책 시나리오 로더

YAML 형식으로 정의된 정책 시나리오를 로드하고 실행하는 모듈입니다.
"""

import os
import yaml
import json
import datetime
from typing import Dict, List, Any, Optional, Union
from decimal import Decimal

from payslip.work_time_schema import (
    TimeCardInputData, TimeCardRecord, WorkTimeCalculationResult
)
from payslip.policy_simulator import PolicySimulator

class ScenarioLoader:
    """
    정책 시나리오 로더 클래스
    
    YAML 형식으로 정의된 정책 시나리오를 로드하고 실행합니다.
    """
    
    def __init__(self, simulator: Optional[PolicySimulator] = None):
        """
        정책 시나리오 로더 초기화
        
        Args:
            simulator: 정책 시뮬레이터 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.simulator = simulator or PolicySimulator()
        self.scenarios = {}
        self.policy_sets = {}
        self.input_data = {}
        self.visualization_settings = {}
    
    def load_scenario_file(self, file_path: str) -> Dict[str, Any]:
        """
        시나리오 파일 로드
        
        Args:
            file_path: 시나리오 파일 경로
            
        Returns:
            로드된 시나리오 데이터
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario_data = yaml.safe_load(f)
        
        # 메타데이터 확인
        metadata = scenario_data.get('metadata', {})
        version = metadata.get('version', '1.0')
        
        # 입력 데이터 로드
        self.input_data = self._load_input_data(scenario_data.get('input_data', {}))
        
        # 정책 조합 로드
        self.policy_sets = self._load_policy_sets(scenario_data.get('policy_sets', {}))
        
        # 시나리오 로드
        self.scenarios = self._load_scenarios(scenario_data.get('scenarios', {}))
        
        # 시각화 설정 로드
        self.visualization_settings = scenario_data.get('visualization', {})
        
        return {
            'metadata': metadata,
            'input_data_count': len(self.input_data),
            'policy_sets_count': len(self.policy_sets),
            'scenarios_count': len(self.scenarios),
            'has_visualization_settings': bool(self.visualization_settings)
        }
    
    def _load_input_data(self, input_data_dict: Dict[str, Any]) -> Dict[str, TimeCardInputData]:
        """
        입력 데이터 로드
        
        Args:
            input_data_dict: 입력 데이터 딕셔너리
            
        Returns:
            로드된 입력 데이터 딕셔너리
        """
        result = {}
        
        for key, data in input_data_dict.items():
            # 레코드 변환
            records = []
            for record_data in data.get('records', []):
                date_str = record_data.get('date')
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                
                record = TimeCardRecord(
                    date=date,
                    start_time=record_data.get('start_time'),
                    end_time=record_data.get('end_time'),
                    break_time_minutes=record_data.get('break_time_minutes', 0),
                    is_holiday=record_data.get('is_holiday', False)
                )
                records.append(record)
            
            # 입사일/퇴사일 변환
            hire_date = data.get('hire_date')
            if hire_date:
                hire_date = datetime.datetime.strptime(hire_date, '%Y-%m-%d').date()
            
            resignation_date = data.get('resignation_date')
            if resignation_date:
                resignation_date = datetime.datetime.strptime(resignation_date, '%Y-%m-%d').date()
            
            # TimeCardInputData 객체 생성
            input_data = TimeCardInputData(
                employee_id=data.get('employee_id', ''),
                period=data.get('period', ''),
                hire_date=hire_date,
                resignation_date=resignation_date,
                records=records
            )
            
            result[key] = input_data
        
        return result
    
    def _load_policy_sets(self, policy_sets_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        정책 조합 로드
        
        Args:
            policy_sets_dict: 정책 조합 딕셔너리
            
        Returns:
            로드된 정책 조합 딕셔너리
        """
        result = {}
        
        for key, data in policy_sets_dict.items():
            result[key] = {
                'name': data.get('name', key),
                'description': data.get('description', ''),
                'policies': data.get('policies', {})
            }
        
        return result
    
    def _load_scenarios(self, scenarios_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        시나리오 로드
        
        Args:
            scenarios_dict: 시나리오 딕셔너리
            
        Returns:
            로드된 시나리오 딕셔너리
        """
        result = {}
        
        for key, data in scenarios_dict.items():
            result[key] = {
                'name': data.get('name', key),
                'description': data.get('description', ''),
                'input': data.get('input', 'default'),
                'policy_sets': data.get('policy_sets', [])
            }
        
        return result
    
    def run_scenario(self, scenario_key: str) -> Dict[str, Any]:
        """
        시나리오 실행
        
        Args:
            scenario_key: 실행할 시나리오 키
            
        Returns:
            시뮬레이션 결과
        """
        if scenario_key not in self.scenarios:
            raise ValueError(f"시나리오 '{scenario_key}'를 찾을 수 없습니다.")
        
        scenario = self.scenarios[scenario_key]
        input_key = scenario['input']
        policy_set_keys = scenario['policy_sets']
        
        if input_key not in self.input_data:
            raise ValueError(f"입력 데이터 '{input_key}'를 찾을 수 없습니다.")
        
        input_data = self.input_data[input_key]
        
        # 정책 조합 목록 생성
        policy_sets = []
        policy_set_names = []
        
        for key in policy_set_keys:
            if key not in self.policy_sets:
                raise ValueError(f"정책 조합 '{key}'를 찾을 수 없습니다.")
            
            policy_set = self.policy_sets[key]
            policy_sets.append(policy_set['policies'])
            policy_set_names.append(policy_set['name'])
        
        # 시뮬레이션 실행
        results = self.simulator.simulate_across_policies(
            input_data=input_data,
            policy_sets=policy_sets,
            policy_set_names=policy_set_names
        )
        
        # 결과에 시나리오 정보 추가
        scenario_info = {
            'scenario_key': scenario_key,
            'scenario_name': scenario['name'],
            'scenario_description': scenario['description'],
            'input_key': input_key,
            'policy_set_keys': policy_set_keys,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        return {
            'scenario_info': scenario_info,
            'results': results
        }
    
    def run_all_scenarios(self) -> Dict[str, Dict[str, Any]]:
        """
        모든 시나리오 실행
        
        Returns:
            모든 시나리오의 시뮬레이션 결과
        """
        results = {}
        
        for scenario_key in self.scenarios:
            results[scenario_key] = self.run_scenario(scenario_key)
        
        return results
    
    def get_visualization_data(self, scenario_results: Dict[str, Any], chart_template: str = None) -> Dict[str, Any]:
        """
        시각화 데이터 생성
        
        Args:
            scenario_results: 시나리오 실행 결과
            chart_template: 차트 템플릿 이름 (제공되지 않으면 기본 템플릿 사용)
            
        Returns:
            시각화 데이터
        """
        if not self.visualization_settings:
            raise ValueError("시각화 설정이 로드되지 않았습니다.")
        
        # 차트 템플릿 선택
        templates = self.visualization_settings.get('chart_templates', [])
        selected_template = None
        
        if chart_template:
            for template in templates:
                if template.get('name') == chart_template:
                    selected_template = template
                    break
        
        if not selected_template and templates:
            selected_template = templates[0]
        
        if not selected_template:
            # 기본 템플릿 생성
            selected_template = {
                'name': 'default',
                'title': '정책 비교',
                'type': self.visualization_settings.get('default_chart_type', 'bar'),
                'metrics': ['regular_hours', 'overtime_hours', 'night_hours', 'holiday_hours', 'total_net_work_hours'],
                'stacked': False
            }
        
        # 메트릭 정보 가져오기
        metrics_info = {}
        for metric in self.visualization_settings.get('metrics', []):
            metrics_info[metric.get('name')] = {
                'display_name': metric.get('display_name', metric.get('name')),
                'color': metric.get('color', '#000000')
            }
        
        # 시각화 데이터 생성
        visualization_data = {
            'chart_type': selected_template.get('type', 'bar'),
            'title': selected_template.get('title', '정책 비교'),
            'stacked': selected_template.get('stacked', False),
            'labels': [],
            'datasets': []
        }
        
        # 결과에서 데이터 추출
        results = scenario_results.get('results', {})
        metrics = selected_template.get('metrics', [])
        
        # 각 메트릭에 대한 데이터셋 생성
        for metric in metrics:
            dataset = {
                'label': metrics_info.get(metric, {}).get('display_name', metric),
                'data': [],
                'backgroundColor': metrics_info.get(metric, {}).get('color', '#000000')
            }
            
            for policy_name, result_data in results.items():
                if not visualization_data['labels']:
                    visualization_data['labels'].append(policy_name)
                
                result = result_data.get('result')
                if result and hasattr(result, 'time_summary'):
                    value = getattr(result.time_summary, metric, Decimal('0'))
                    dataset['data'].append(float(value))
            
            visualization_data['datasets'].append(dataset)
        
        return visualization_data
    
    def save_visualization_data(self, visualization_data: Dict[str, Any], output_path: str) -> str:
        """
        시각화 데이터 저장
        
        Args:
            visualization_data: 시각화 데이터
            output_path: 출력 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(visualization_data, f, ensure_ascii=False, indent=2)
        
        return output_path


# 사용 예시
if __name__ == "__main__":
    # 시나리오 로더 생성
    loader = ScenarioLoader()
    
    # 시나리오 파일 로드
    scenario_file = "tests/fixtures/policy_scenarios.yaml"
    loader.load_scenario_file(scenario_file)
    
    # 시나리오 실행
    scenario_key = "basic_comparison"
    results = loader.run_scenario(scenario_key)
    
    # 시각화 데이터 생성
    visualization_data = loader.get_visualization_data(results, "hours_comparison")
    
    # 시각화 데이터 저장
    output_path = "visualization_data.json"
    loader.save_visualization_data(visualization_data, output_path)
    
    print(f"시나리오 '{scenario_key}' 실행 완료!")
    print(f"시각화 데이터 저장 경로: {output_path}")
