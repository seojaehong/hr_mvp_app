# /home/ubuntu/upload/tests/test_attendance_calculator.py
"""
Plan 020: 듀얼 모드 근로시간 계산기 - AttendanceBasedCalculator 테스트

이 파일은 AttendanceBasedCalculator 클래스의 기능을 테스트합니다.
"""

import unittest
import datetime
from decimal import Decimal
from typing import Dict, List, Optional

# 테스트 대상 모듈 import
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from payslip.attendance_calculator import AttendanceBasedCalculator
from payslip.work_time_schema import WorkTimeSettings, AttendanceInputRecord

class TestAttendanceBasedCalculator(unittest.TestCase):
    """AttendanceBasedCalculator 클래스의 기능을 테스트하는 테스트 케이스"""

    def setUp(self):
        """각 테스트 실행 전 설정"""
        self.test_settings: WorkTimeSettings = {
            "company_id": "TEST_COMP_ATT",
            "default_daily_scheduled_hours": Decimal("8.0"),
            "default_weekly_scheduled_hours": Decimal("40.0"),
            "overtime_rules": {},
            "night_work_rules": {},
            "holiday_rules": {
                "public_holidays": {
                    "2025-05": ["2025-05-01", "2025-05-05", "2025-05-15"] # 가정
                }
            },
            "break_time_rules": [],
            "attendance_status_codes": {
                "1": {"work_day_value": Decimal("1.0"), "is_paid_leave": False, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "정상근무"},
                "0.5A": {"work_day_value": Decimal("0.5"), "is_paid_leave": True, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "오전 유급반차"},
                "0.5P": {"work_day_value": Decimal("0.5"), "is_paid_leave": True, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "오후 유급반차"},
                "0": {"work_day_value": Decimal("0.0"), "is_paid_leave": False, "is_unpaid_leave": True, "counts_as_late": False, "counts_as_early_leave": False, "description": "무급결근"},
                "L": {"work_day_value": Decimal("1.0"), "is_paid_leave": False, "is_unpaid_leave": False, "counts_as_late": True, "counts_as_early_leave": False, "description": "지각 (정상근무로 처리)"},
                "E": {"work_day_value": Decimal("1.0"), "is_paid_leave": False, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": True, "description": "조퇴 (정상근무로 처리)"},
                "SICK_P": {"work_day_value": Decimal("1.0"), "is_paid_leave": True, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "유급병가"},
                "SICK_U": {"work_day_value": Decimal("0.0"), "is_paid_leave": False, "is_unpaid_leave": True, "counts_as_late": False, "counts_as_early_leave": False, "description": "무급병가"}
            }
        }
        self.calculator = AttendanceBasedCalculator(settings=self.test_settings)

    def test_calculate_basic_attendance(self):
        """기본 출근 상태 데이터 계산 테스트"""
        sample_data: List[AttendanceInputRecord] = [
            {"date": "2025-05-02", "status_code": "1"},       # 평일
            {"date": "2025-05-03", "status_code": "1"},       # 토요일 (소정근로일 아님)
            {"date": "2025-05-06", "status_code": "0.5A"},    # 평일 오전반차
            {"date": "2025-05-07", "status_code": "L"},       # 평일 지각
            {"date": "2025-05-08", "status_code": "0"},       # 평일 결근
            {"date": "2025-05-01", "status_code": "SICK_P"} # 공휴일 + 유급병가
        ]
        period_info = {"period": "2025-05"}
        result = self.calculator.calculate(sample_data, period_info)

        self.assertIsNone(result.get("error"))
        self.assertIsNotNone(result.get("work_summary"))
        self.assertIsNotNone(result.get("salary_basis"))

        work_summary = result["work_summary"]
        # 2025년 5월: 총 31일, 공휴일 3일 (1,5,15), 주말 8일 (3,4,10,11,17,18,24,25,31(토)).
        # 소정근로일 = 31 - 8(주말) - 3(공휴일) = 20일
        self.assertEqual(work_summary["total_days_in_period"], 31)
        self.assertEqual(work_summary["scheduled_work_days"], 20) 
        self.assertEqual(work_summary["actual_work_days"], Decimal("3.5")) # 1(5/2) + 0.5(5/6) + 1(5/7) + 1(5/1 공휴일병가) 
        self.assertEqual(work_summary["paid_leave_days"], Decimal("1.5")) # 0.5(5/6) + 1(5/1)
        self.assertEqual(work_summary["unpaid_leave_days"], Decimal("1.0")) # 1(5/8)
        self.assertEqual(work_summary["late_count"], 1)
        self.assertEqual(work_summary["early_leave_count"], 0)

        salary_basis = result["salary_basis"]
        # payment_target_days = scheduled_work_days - unpaid_leave_days = 20 - 1 = 19
        self.assertEqual(salary_basis["payment_target_days"], Decimal("19.0"))
        self.assertEqual(salary_basis["deduction_days"], Decimal("1.0"))

    def test_calculate_with_unknown_status_code(self):
        """알 수 없는 상태 코드 포함 시 경고 발생 테스트"""
        sample_data: List[AttendanceInputRecord] = [
            {"date": "2025-05-02", "status_code": "1"},
            {"date": "2025-05-06", "status_code": "UNKNOWN"}
        ]
        period_info = {"period": "2025-05"}
        result = self.calculator.calculate(sample_data, period_info)

        self.assertIsNone(result.get("error"))
        self.assertTrue(len(result.get("warnings", [])) > 0)
        self.assertIn("Unknown status_code \'UNKNOWN\'. Will be ignored.", result["warnings"][0])
        # UNKNOWN 코드는 무시되므로 actual_work_days는 1일
        self.assertEqual(result["work_summary"]["actual_work_days"], Decimal("1.0"))

    def test_calculate_empty_data(self):
        """입력 데이터가 비어있는 경우 테스트"""
        sample_data: List[AttendanceInputRecord] = []
        period_info = {"period": "2025-05"}
        result = self.calculator.calculate(sample_data, period_info)
        
        self.assertIsNone(result.get("error"))
        work_summary = result["work_summary"]
        self.assertEqual(work_summary["actual_work_days"], Decimal("0.0"))
        self.assertEqual(work_summary["paid_leave_days"], Decimal("0.0"))
        self.assertEqual(work_summary["unpaid_leave_days"], Decimal("0.0"))

    def test_get_days_in_month(self):
        """월별 총 일수 계산 함수 테스트"""
        self.assertEqual(self.calculator._get_days_in_month("2025-01"), 31)
        self.assertEqual(self.calculator._get_days_in_month("2025-02"), 28) # 2025년은 평년
        self.assertEqual(self.calculator._get_days_in_month("2024-02"), 29) # 2024년은 윤년
        self.assertEqual(self.calculator._get_days_in_month("2025-12"), 31)

    def test_get_scheduled_work_days(self):
        """소정근로일수 계산 함수 테스트"""
        # 2025년 5월: 총 31일, 공휴일 3일 (1,5,15), 주말 8일. 소정근로일 = 31 - 8 - 3 = 20일
        days_in_may_2025 = self.calculator._get_days_in_month("2025-05")
        self.assertEqual(self.calculator._get_scheduled_work_days("2025-05", days_in_may_2025), 20)
        
        # 2025년 2월: 총 28일, 공휴일 없음 가정, 주말 8일. 소정근로일 = 28 - 8 = 20일
        # holiday_rules에 2025-02가 없으므로 공휴일 0으로 계산됨
        days_in_feb_2025 = self.calculator._get_days_in_month("2025-02")
        self.assertEqual(self.calculator._get_scheduled_work_days("2025-02", days_in_feb_2025), 20)

if __name__ == '__main__':
    unittest.main()
