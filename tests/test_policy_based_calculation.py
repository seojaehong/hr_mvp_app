"""
정책 기반 시뮬레이션 테스트

정책 기반 시뮬레이션을 위한 자동화 테스트를 제공합니다.
"""

import pytest
import os
from decimal import Decimal
from typing import Dict, List, Any

from payslip.timecard_calculator_refactored import TimeCardBasedCalculator
from payslip.policy_manager import PolicyManager
from tests.test_utils import (
    load_timecard_test_cases,
    create_input_data_from_test_case,
    create_policy_manager_from_test_case,
    verify_result
)

# 테스트 케이스 로드
test_cases = load_timecard_test_cases()

# 테스트 케이스 ID 목록
test_case_ids = [case.get("id") for case in test_cases]

@pytest.mark.parametrize("test_case", test_cases, ids=test_case_ids)
def test_policy_based_calculation(test_case):
    """
    정책 기반 계산 테스트
    
    Args:
        test_case: 테스트 케이스 딕셔너리
    """
    # 테스트 케이스 정보 출력
    print(f"\nRunning test: {test_case.get('id')} - {test_case.get('description')}")
    
    # 입력 데이터 생성
    input_data = create_input_data_from_test_case(test_case)
    
    # 정책 관리자 생성
    policy_manager = create_policy_manager_from_test_case(test_case)
    
    # 계산기 생성 및 계산 실행
    calculator = TimeCardBasedCalculator(policy_manager=policy_manager)
    result = calculator.calculate(input_data)
    
    # 결과 검증
    expected_output = test_case.get("expected_output", {})
    errors = verify_result(result, expected_output)
    
    # 오류가 있으면 실패
    assert not errors, f"Test failed with errors: {errors}"
    
    # 테스트 통과 메시지
    print(f"Test passed: {test_case.get('id')}")

def test_all_test_cases_loaded():
    """
    모든 테스트 케이스가 로드되었는지 확인
    """
    assert len(test_cases) > 0, "No test cases loaded"
    print(f"Loaded {len(test_cases)} test cases")
    
    # 테스트 케이스 ID 목록 출력
    for i, case_id in enumerate(test_case_ids):
        print(f"{i+1}. {case_id}")

if __name__ == "__main__":
    # 직접 실행 시 모든 테스트 실행
    pytest.main(["-v", __file__])
