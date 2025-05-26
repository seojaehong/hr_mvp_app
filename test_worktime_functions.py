# tests/worktime/test_worktime_functions.py
import sys
import os

# 프로젝트 루트 경로를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from Payslip.Worktime.processor import WorkTimeProcessor
import logging
import datetime
from decimal import Decimal

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 테스트 설정
settings = {
    "company_id": "TEST_COMP",
    "company_settings": {
        "daily_work_minutes_standard": 480,  # 8시간
        "weekly_work_minutes_standard": 2400,  # 40시간
        "night_shift_start_time": "22:00",
        "night_shift_end_time": "06:00",
        "break_time_rules": [
            {"threshold_minutes": 240, "break_minutes": 30},  # 4시간 이상 근무 시 30분 휴게
            {"threshold_minutes": 480, "break_minutes": 60}   # 8시간 이상 근무 시 60분 휴게
        ]
    },
    "attendance_status_codes": {
        "1": {"work_day_value": 1.0, "is_paid_leave": False, "is_unpaid_leave": False, "description": "정상 출근"},
        "2": {"work_day_value": 0.0, "is_paid_leave": False, "is_unpaid_leave": True, "description": "결근"},
        "3": {"work_day_value": 1.0, "is_paid_leave": True, "is_unpaid_leave": False, "description": "유급 휴가"},
        "4": {"work_day_value": 0.0, "is_paid_leave": False, "is_unpaid_leave": True, "description": "무급 휴가"},
        "5": {"work_day_value": 0.5, "is_paid_leave": False, "is_unpaid_leave": False, "description": "반차", "counts_as_early_leave": True}
    }
}

def test_attendance_based_calculator():
    """출결 기반 계산기(모드 A) 테스트"""
    print("\n===== 출결 기반 계산기(모드 A) 테스트 =====")
    
    # 프로세서 초기화
    processor = WorkTimeProcessor(settings)
    
    # 테스트 데이터
    attendance_data = [
        {"date": "2025-05-01", "status_code": "1"},  # 정상 출근
        {"date": "2025-05-02", "status_code": "1"},  # 정상 출근
        {"date": "2025-05-03", "status_code": "2"},  # 결근
        {"date": "2025-05-04", "status_code": "3"},  # 유급 휴가
        {"date": "2025-05-05", "status_code": "5"}   # 반차
    ]
    
    # 테스트 실행
    result = processor.process(
        input_data=attendance_data,
        period="2025-05",
        employee_id="EMP001",
        mode="attendance"
    )
    
    # 결과 출력
    print(f"처리 모드: {result.processing_mode}")
    if result.attendance_summary:
        print(f"총 일수: {result.attendance_summary.total_days_in_period}")
        print(f"예정 근무일수: {result.attendance_summary.scheduled_work_days}")
        print(f"실제 근무일수: {result.attendance_summary.actual_work_days}")
        print(f"전일 근무일수: {result.attendance_summary.full_work_days}")
        print(f"유급 휴가일수: {result.attendance_summary.paid_leave_days}")
        print(f"무급 휴가일수: {result.attendance_summary.unpaid_leave_days}")
    
    if result.salary_basis:
        print(f"급여 계산 기준 일수: {result.salary_basis.payment_target_days}")
        print(f"공제 일수: {result.salary_basis.deduction_days}")
    
    print(f"경고: {result.warnings}")
    print(f"오류: {result.error}")

def test_timecard_based_calculator():
    """타임카드 기반 계산기(모드 B) 테스트"""
    print("\n===== 타임카드 기반 계산기(모드 B) 테스트 =====")
    
    # 프로세서 초기화
    processor = WorkTimeProcessor(settings)
    
    # 테스트 데이터
    timecard_data = [
        {"date": "2025-05-01", "start_time": "09:00", "end_time": "18:00", "break_time_minutes": 60},  # 정상 근무
        {"date": "2025-05-02", "start_time": "09:00", "end_time": "20:00", "break_time_minutes": 60},  # 연장 근무
        {"date": "2025-05-03", "start_time": "21:00", "end_time": "06:00", "break_time_minutes": 60},  # 야간 근무
        {"date": "2025-05-04", "start_time": "10:00", "end_time": "15:00", "break_time_minutes": 30}   # 단축 근무
    ]
    
    # 테스트 실행
    result = processor.process(
        input_data=timecard_data,
        period="2025-05",
        employee_id="EMP002",
        mode="timecard",
        holiday_dates=["2025-05-05"]  # 휴일 정보
    )
    
    # 결과 출력
    print(f"처리 모드: {result.processing_mode}")
    if result.time_summary:
        print(f"정규 근무시간: {result.time_summary.regular_hours}시간")
        print(f"연장 근무시간: {result.time_summary.overtime_hours}시간")
        print(f"야간 근무시간: {result.time_summary.night_hours}시간")
        print(f"휴일 근무시간: {result.time_summary.holiday_hours}시간")
        print(f"총 실근로시간: {result.time_summary.total_net_work_hours}시간")
    
    if result.daily_calculation_details:
        print("\n일별 상세 정보:")
        for detail in result.daily_calculation_details:
            print(f"날짜: {detail.date}, 정규: {detail.regular_hours}시간, 연장: {detail.overtime_hours}시간, 야간: {detail.night_hours}시간")
    
    print(f"경고: {result.warnings}")
    print(f"오류: {result.error}")

def test_edge_cases():
    """경계 상황 테스트"""
    print("\n===== 경계 상황 테스트 =====")
    
    # 프로세서 초기화
    processor = WorkTimeProcessor(settings)
    
    # 1. 빈 입력 데이터
    print("\n1. 빈 입력 데이터 테스트")
    empty_result = processor.process(
        input_data=[],
        period="2025-05",
        employee_id="EMP003"
    )
    print(f"처리 모드: {empty_result.processing_mode}")
    print(f"오류: {empty_result.error}")
    
    # 2. 잘못된 상태 코드
    print("\n2. 잘못된 상태 코드 테스트")
    invalid_code_result = processor.process(
        input_data=[{"date": "2025-05-01", "status_code": "X"}],
        period="2025-05",
        employee_id="EMP004",
        mode="attendance"
    )
    print(f"처리 모드: {invalid_code_result.processing_mode}")
    print(f"경고: {invalid_code_result.warnings}")
    
    # 3. 잘못된 시간 형식
    print("\n3. 잘못된 시간 형식 테스트")
    try:
        invalid_time_result = processor.process(
            input_data=[{"date": "2025-05-01", "start_time": "9:00", "end_time": "18:00"}],
            period="2025-05",
            employee_id="EMP005",
            mode="timecard"
        )
        print(f"처리 모드: {invalid_time_result.processing_mode}")
        print(f"오류: {invalid_time_result.error}")
    except Exception as e:
        print(f"예외 발생: {str(e)}")

if __name__ == "__main__":
    # 출결 기반 계산기 테스트
    test_attendance_based_calculator()
    
    # 타임카드 기반 계산기 테스트
    # 참고: 현재 구현에서는 타임카드 기반 계산기가 완전히 구현되지 않았을 수 있음
    test_timecard_based_calculator()
    
    # 경계 상황 테스트
    test_edge_cases()
