"""
테스트 유틸리티 모듈

정책 기반 시뮬레이션을 위한 테스트 케이스 로딩 및 관리 유틸리티를 제공합니다.
"""

import os
import yaml
import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union

from payslip.work_time_schema import (
    TimeCardInputData, TimeCardRecord, WorkTimeCalculationResult,
    TimeSummary, WorkDayDetail, ErrorDetails, ComplianceAlert
)
from payslip.policy_manager import PolicyManager

def load_timecard_test_cases(path: str = None) -> List[Dict[str, Any]]:
    """
    타임카드 테스트 케이스 로드
    
    Args:
        path: 테스트 케이스 YAML 파일 경로 (기본값: tests/fixtures/timecard_cases.yaml)
        
    Returns:
        테스트 케이스 목록
    """
    if path is None:
        # 기본 경로 설정
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        path = os.path.join(base_dir, "tests", "fixtures", "timecard_cases.yaml")
    
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    return data.get("test_cases", [])

def create_input_data_from_test_case(test_case: Dict[str, Any]) -> TimeCardInputData:
    """
    테스트 케이스에서 TimeCardInputData 객체 생성
    
    Args:
        test_case: 테스트 케이스 딕셔너리
        
    Returns:
        TimeCardInputData 객체
    """
    input_data = test_case.get("input", {})
    
    # 날짜 객체 변환
    hire_date = input_data.get("hire_date")
    if hire_date:
        hire_date = datetime.datetime.strptime(hire_date, "%Y-%m-%d").date()
    
    resignation_date = input_data.get("resignation_date")
    if resignation_date:
        resignation_date = datetime.datetime.strptime(resignation_date, "%Y-%m-%d").date()
    
    # 레코드 변환
    records = []
    for record in input_data.get("records", []):
        date = datetime.datetime.strptime(record.get("date"), "%Y-%m-%d").date()
        records.append(TimeCardRecord(
            date=date,
            start_time=record.get("start_time"),
            end_time=record.get("end_time"),
            break_time_minutes=record.get("break_time_minutes")
        ))
    
    return TimeCardInputData(
        employee_id=input_data.get("employee_id"),
        period=input_data.get("period"),
        hire_date=hire_date,
        resignation_date=resignation_date,
        records=records
    )

def create_policy_manager_from_test_case(test_case: Dict[str, Any]) -> PolicyManager:
    """
    테스트 케이스에서 PolicyManager 객체 생성
    
    Args:
        test_case: 테스트 케이스 딕셔너리
        
    Returns:
        PolicyManager 객체
    """
    policy_settings = test_case.get("policy_settings", {})
    
    # PolicyManager 생성
    policy_manager = PolicyManager()
    
    # 정책 설정 적용
    for key, value in _flatten_dict(policy_settings).items():
        policy_manager.set(key, value)
    
    return policy_manager

def _flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    중첩된 딕셔너리를 평탄화
    
    Args:
        d: 중첩된 딕셔너리
        parent_key: 부모 키
        sep: 키 구분자
        
    Returns:
        평탄화된 딕셔너리
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)

def verify_result(result: WorkTimeCalculationResult, expected: Dict[str, Any]) -> List[str]:
    """
    계산 결과와 기대 출력 비교
    
    Args:
        result: 계산 결과
        expected: 기대 출력
        
    Returns:
        오류 메시지 목록 (비어있으면 검증 성공)
    """
    errors = []
    
    # 상태 확인
    expected_status = expected.get("status", "success")
    if expected_status == "error":
        if result.processing_mode != "error":
            errors.append(f"Expected error status, got {result.processing_mode}")
        
        expected_error_code = expected.get("error_code")
        if expected_error_code and result.error and result.error.error_code != expected_error_code:
            errors.append(f"Expected error code {expected_error_code}, got {result.error.error_code if result.error else 'None'}")
        
        expected_message = expected.get("message")
        if expected_message and result.error and result.error.message != expected_message:
            errors.append(f"Expected error message '{expected_message}', got '{result.error.message if result.error else 'None'}'")
        
        return errors
    
    # 시간 요약 확인
    expected_regular_hours = Decimal(str(expected.get("regular_hours", 0)))
    if result.time_summary.regular_hours != expected_regular_hours:
        errors.append(f"Expected regular_hours {expected_regular_hours}, got {result.time_summary.regular_hours}")
    
    expected_overtime_hours = Decimal(str(expected.get("overtime_hours", 0)))
    if result.time_summary.overtime_hours != expected_overtime_hours:
        errors.append(f"Expected overtime_hours {expected_overtime_hours}, got {result.time_summary.overtime_hours}")
    
    expected_night_hours = Decimal(str(expected.get("night_hours", 0)))
    if result.time_summary.night_hours != expected_night_hours:
        errors.append(f"Expected night_hours {expected_night_hours}, got {result.time_summary.night_hours}")
    
    expected_holiday_hours = Decimal(str(expected.get("holiday_hours", 0)))
    if result.time_summary.holiday_hours != expected_holiday_hours:
        errors.append(f"Expected holiday_hours {expected_holiday_hours}, got {result.time_summary.holiday_hours}")
    
    expected_holiday_overtime_hours = Decimal(str(expected.get("holiday_overtime_hours", 0)))
    if result.time_summary.holiday_overtime_hours != expected_holiday_overtime_hours:
        errors.append(f"Expected holiday_overtime_hours {expected_holiday_overtime_hours}, got {result.time_summary.holiday_overtime_hours}")
    
    expected_total_hours = Decimal(str(expected.get("total_hours", 0)))
    if result.time_summary.total_net_work_hours != expected_total_hours:
        errors.append(f"Expected total_hours {expected_total_hours}, got {result.time_summary.total_net_work_hours}")
    
    # 경고 메시지 확인
    expected_warnings = expected.get("warnings", [])
    if len(expected_warnings) != len(result.warnings):
        errors.append(f"Expected {len(expected_warnings)} warnings, got {len(result.warnings)}")
    else:
        for expected_warning in expected_warnings:
            if expected_warning not in result.warnings:
                errors.append(f"Expected warning '{expected_warning}' not found")
    
    # 컴플라이언스 알림 확인
    expected_alerts = expected.get("compliance_alerts", [])
    if len(expected_alerts) != len(result.compliance_alerts):
        errors.append(f"Expected {len(expected_alerts)} compliance alerts, got {len(result.compliance_alerts)}")
    else:
        for i, expected_alert in enumerate(expected_alerts):
            if i >= len(result.compliance_alerts):
                errors.append(f"Expected compliance alert {i+1} not found")
                continue
            
            alert = result.compliance_alerts[i]
            expected_alert_code = expected_alert.get("alert_code")
            if expected_alert_code and alert.alert_code != expected_alert_code:
                errors.append(f"Expected compliance alert code {expected_alert_code}, got {alert.alert_code}")
            
            expected_severity = expected_alert.get("severity")
            if expected_severity and alert.severity != expected_severity:
                errors.append(f"Expected compliance alert severity {expected_severity}, got {alert.severity}")
    
    return errors
