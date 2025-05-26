"""
확장된 정책 시나리오 로더

확장된 YAML 형식으로 정의된 정책 시나리오를 로드하고 검증하는 모듈입니다.
정책 스키마, 의존성, 적용 조건, 상태 관리 등 확장된 기능을 지원합니다.
"""

import os
import yaml
import json
import datetime
import re
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from decimal import Decimal
from dataclasses import dataclass, field

from Payslip.work_time_schema import (  
    TimeCardInputData, TimeCardRecord, WorkTimeCalculationResult
)
from Payslip.policy_simulator import PolicySimulator
from Payslip.policy_manager import PolicyManager

@dataclass
class PolicySchemaInfo:
    """정책 스키마 정보"""
    type: str
    default: Any
    description: str
    legal_reference: str
    validation: Dict[str, Any]
    impact_level: str
    category: str
    status: str
    applicability_condition: str
    conflicts_with: List[str] = field(default_factory=list)
    related_policies: List[str] = field(default_factory=list)

@dataclass
class PolicyDependencyInfo:
    """정책 의존성 정보"""
    depends_on: List[str] = field(default_factory=list)
    affects: List[str] = field(default_factory=list)
    conflicts_with: List[str] = field(default_factory=list)

@dataclass
class EmploymentTypeInfo:
    """고용형태 정보"""
    name: str
    description: str
    applicable_policies: List[str] = field(default_factory=list)

@dataclass
class PolicySetInfo:
    """정책 조합 정보"""
    name: str
    description: str
    policies: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ScenarioInfo:
    """시나리오 정보"""
    name: str
    description: str
    input: str
    policy_sets: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)
    analysis_focus: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class ValidationError:
    """검증 오류 정보"""
    error_type: str
    message: str
    policy_key: Optional[str] = None
    policy_set: Optional[str] = None
    scenario: Optional[str] = None
    field: Optional[str] = None

class EnhancedScenarioLoader:
    """
    확장된 정책 시나리오 로더 클래스
    
    확장된 YAML 형식으로 정의된 정책 시나리오를 로드하고 검증합니다.
    """
    
    def __init__(self, simulator: Optional[PolicySimulator] = None, policy_manager: Optional[PolicyManager] = None):
        """
        확장된 정책 시나리오 로더 초기화
        
        Args:
            simulator: 정책 시뮬레이터 인스턴스 (제공되지 않으면 새로 생성)
            policy_manager: 정책 관리자 인스턴스 (제공되지 않으면 새로 생성)
        """
        self.simulator = simulator or PolicySimulator()
        self.policy_manager = policy_manager or PolicyManager()
        
        # 데이터 저장소
        self.metadata = {}
        self.policy_schema = {}
        self.policy_dependencies = {}
        self.employment_types = {}
        self.input_data = {}
        self.policy_sets = {}
        self.scenarios = {}
        self.visualization_settings = {}
        self.comparison_settings = {}
        self.policy_snapshot_settings = {}
        
        # 검증 오류 저장소
        self.validation_errors = []
    
    def load_scenario_file(self, file_path: str) -> Dict[str, Any]:
        """
        시나리오 파일 로드
        
        Args:
            file_path: 시나리오 파일 경로
            
        Returns:
            로드된 시나리오 데이터 요약
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            scenario_data = yaml.safe_load(f)
        
        # 메타데이터 로드
        self.metadata = scenario_data.get('metadata', {})
        
        # 정책 스키마 로드
        self.policy_schema = self._load_policy_schema(scenario_data.get('policy_schema', {}))
        
        # 정책 의존성 로드
        self.policy_dependencies = self._load_policy_dependencies(scenario_data.get('policy_dependencies', {}))
        
        # 고용형태 정보 로드
        self.employment_types = self._load_employment_types(scenario_data.get('employment_type_policies', {}))
        
        # 입력 데이터 로드
        self.input_data = self._load_input_data(scenario_data.get('input_data', {}))
        
        # 정책 조합 로드
        self.policy_sets = self._load_policy_sets(scenario_data.get('policy_sets', {}))
        
        # 시나리오 로드
        self.scenarios = self._load_scenarios(scenario_data.get('scenarios', {}))
        
        # 시각화 설정 로드
        self.visualization_settings = scenario_data.get('visualization', {})
        
        # 비교 설정 로드
        self.comparison_settings = scenario_data.get('comparison_settings', {})
        
        # 정책 스냅샷 설정 로드
        self.policy_snapshot_settings = scenario_data.get('policy_snapshot', {})
        
        # 데이터 검증
        self._validate_loaded_data()
        
        return {
            'metadata': self.metadata,
            'policy_schema_count': len(self.policy_schema),
            'policy_dependencies_count': len(self.policy_dependencies),
            'employment_types_count': len(self.employment_types),
            'input_data_count': len(self.input_data),
            'policy_sets_count': len(self.policy_sets),
            'scenarios_count': len(self.scenarios),
            'has_visualization_settings': bool(self.visualization_settings),
            'has_comparison_settings': bool(self.comparison_settings),
            'has_policy_snapshot_settings': bool(self.policy_snapshot_settings),
            'validation_errors_count': len(self.validation_errors)
        }
    
    def _load_policy_schema(self, schema_dict: Dict[str, Any]) -> Dict[str, PolicySchemaInfo]:
        """
        정책 스키마 로드
        
        Args:
            schema_dict: 정책 스키마 딕셔너리
            
        Returns:
            로드된 정책 스키마 딕셔너리
        """
        result = {}
        
        for key, data in schema_dict.items():
            schema_info = PolicySchemaInfo(
                type=data.get('type', 'string'),
                default=data.get('default'),
                description=data.get('description', ''),
                legal_reference=data.get('legal_reference', ''),
                validation=data.get('validation', {}),
                impact_level=data.get('impact_level', 'medium'),
                category=data.get('category', ''),
                status=data.get('status', 'active'),
                applicability_condition=data.get('applicability_condition', 'true'),
                conflicts_with=data.get('conflicts_with', []),
                related_policies=data.get('related_policies', [])
            )
            result[key] = schema_info
        
        return result
    
    def _load_policy_dependencies(self, dependencies_dict: Dict[str, Any]) -> Dict[str, PolicyDependencyInfo]:
        """
        정책 의존성 로드
        
        Args:
            dependencies_dict: 정책 의존성 딕셔너리
            
        Returns:
            로드된 정책 의존성 딕셔너리
        """
        result = {}
        
        for key, data in dependencies_dict.items():
            dependency_info = PolicyDependencyInfo(
                depends_on=data.get('depends_on', []),
                affects=data.get('affects', []),
                conflicts_with=data.get('conflicts_with', [])
            )
            result[key] = dependency_info
        
        return result
    
    def _load_employment_types(self, employment_types_dict: Dict[str, Any]) -> Dict[str, EmploymentTypeInfo]:
        """
        고용형태 정보 로드
        
        Args:
            employment_types_dict: 고용형태 정보 딕셔너리
            
        Returns:
            로드된 고용형태 정보 딕셔너리
        """
        result = {}
        
        for key, data in employment_types_dict.items():
            employment_type_info = EmploymentTypeInfo(
                name=data.get('name', key),
                description=data.get('description', ''),
                applicable_policies=data.get('applicable_policies', [])
            )
            result[key] = employment_type_info
        
        return result
    
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
            
            # 확장 필드 추출
            employment_type = data.get('employment_type', 'regular')
            company_size = data.get('company_size', 10)
            weekly_hours = data.get('weekly_hours', 40)
            metadata = data.get('metadata', {})
            
            # TimeCardInputData 객체 생성
            input_data = TimeCardInputData(
                employee_id=data.get('employee_id', ''),
                period=data.get('period', ''),
                hire_date=hire_date,
                resignation_date=resignation_date,
                records=records
            )
            
            # 확장 필드 추가 (커스텀 필드로 저장)
            input_data.custom_fields = {
                'employment_type': employment_type,
                'company_size': company_size,
                'weekly_hours': weekly_hours,
                'metadata': metadata
            }
            
            result[key] = input_data
        
        return result
    
    def _load_policy_sets(self, policy_sets_dict: Dict[str, Any]) -> Dict[str, PolicySetInfo]:
        """
        정책 조합 로드
        
        Args:
            policy_sets_dict: 정책 조합 딕셔너리
            
        Returns:
            로드된 정책 조합 딕셔너리
        """
        result = {}
        
        for key, data in policy_sets_dict.items():
            policy_set_info = PolicySetInfo(
                name=data.get('name', key),
                description=data.get('description', ''),
                policies=data.get('policies', {}),
                metadata=data.get('metadata', {})
            )
            result[key] = policy_set_info
        
        return result
    
    def _load_scenarios(self, scenarios_dict: Dict[str, Any]) -> Dict[str, ScenarioInfo]:
        """
        시나리오 로드
        
        Args:
            scenarios_dict: 시나리오 딕셔너리
            
        Returns:
            로드된 시나리오 딕셔너리
        """
        result = {}
        
        for key, data in scenarios_dict.items():
            scenario_info = ScenarioInfo(
                name=data.get('name', key),
                description=data.get('description', ''),
                input=data.get('input', 'default'),
                policy_sets=data.get('policy_sets', []),
                metadata=data.get('metadata', {}),
                analysis_focus=data.get('analysis_focus', [])
            )
            result[key] = scenario_info
        
        return result
    
    def _validate_loaded_data(self) -> None:
        """
        로드된 데이터 검증
        
        정책 스키마, 의존성, 정책 조합, 시나리오 등의 유효성을 검증합니다.
        """
        self.validation_errors = []
        
        # 정책 스키마 검증
        self._validate_policy_schema()
        
        # 정책 의존성 검증
        self._validate_policy_dependencies()
        
        # 고용형태 정보 검증
        self._validate_employment_types()
        
        # 입력 데이터 검증
        self._validate_input_data()
        
        # 정책 조합 검증
        self._validate_policy_sets()
        
        # 시나리오 검증
        self._validate_scenarios()
    
    def _validate_policy_schema(self) -> None:
        """정책 스키마 검증"""
        for key, schema in self.policy_schema.items():
            # 타입 검증
            if schema.type not in ['string', 'integer', 'float', 'boolean']:
                self.validation_errors.append(ValidationError(
                    error_type='schema_type_invalid',
                    message=f"정책 스키마 '{key}'의 타입 '{schema.type}'이 유효하지 않습니다.",
                    policy_key=key,
                    field='type'
                ))
            
            # 기본값 타입 검증
            if schema.default is not None:
                if schema.type == 'string' and not isinstance(schema.default, str):
                    self.validation_errors.append(ValidationError(
                        error_type='schema_default_type_mismatch',
                        message=f"정책 스키마 '{key}'의 기본값 타입이 스키마 타입과 일치하지 않습니다.",
                        policy_key=key,
                        field='default'
                    ))
                elif schema.type == 'integer' and not isinstance(schema.default, int):
                    self.validation_errors.append(ValidationError(
                        error_type='schema_default_type_mismatch',
                        message=f"정책 스키마 '{key}'의 기본값 타입이 스키마 타입과 일치하지 않습니다.",
                        policy_key=key,
                        field='default'
                    ))
                elif schema.type == 'float' and not isinstance(schema.default, (int, float)):
                    self.validation_errors.append(ValidationError(
                        error_type='schema_default_type_mismatch',
                        message=f"정책 스키마 '{key}'의 기본값 타입이 스키마 타입과 일치하지 않습니다.",
                        policy_key=key,
                        field='default'
                    ))
                elif schema.type == 'boolean' and not isinstance(schema.default, bool):
                    self.validation_errors.append(ValidationError(
                        error_type='schema_default_type_mismatch',
                        message=f"정책 스키마 '{key}'의 기본값 타입이 스키마 타입과 일치하지 않습니다.",
                        policy_key=key,
                        field='default'
                    ))
            
            # 유효성 검증 규칙 검증
            if schema.validation:
                validation_type = schema.validation.get('type')
                if validation_type == 'enum' and 'allowed_values' not in schema.validation:
                    self.validation_errors.append(ValidationError(
                        error_type='schema_validation_invalid',
                        message=f"정책 스키마 '{key}'의 enum 유효성 검증 규칙에 allowed_values가 없습니다.",
                        policy_key=key,
                        field='validation'
                    ))
                elif validation_type == 'range':
                    if 'min' not in schema.validation or 'max' not in schema.validation:
                        self.validation_errors.append(ValidationError(
                            error_type='schema_validation_invalid',
                            message=f"정책 스키마 '{key}'의 range 유효성 검증 규칙에 min 또는 max가 없습니다.",
                            policy_key=key,
                            field='validation'
                        ))
            
            # 상태 검증
            if schema.status not in ['active', 'deprecated', 'draft']:
                self.validation_errors.append(ValidationError(
                    error_type='schema_status_invalid',
                    message=f"정책 스키마 '{key}'의 상태 '{schema.status}'가 유효하지 않습니다.",
                    policy_key=key,
                    field='status'
                ))
            
# 적용 조건 검증
            try:
                self._validate_condition_expression(schema.applicability_condition)
            except Exception as e:
                self.validation_errors.append(ValidationError(
                    error_type='condition_validation_error',  # 예시 오류 타입
                    message=f"정책 스키마 '{key}'의 적용 조건 ('{schema.applicability_condition}') 검증 중 오류: {e}", # 상세한 오류 메시지
                    policy_key=key,                           # 현재 검사 중인 정책의 키
                    field='applicability_condition'           # 오류가 발생한 필드명
                ))