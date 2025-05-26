# /home/ubuntu/upload/tests/test_work_time_processor.py
"""
Plan 020: 듀얼 모드 근로시간 계산기 - WorkTimeProcessor 테스트

이 파일은 WorkTimeProcessor 클래스의 기능을 테스트합니다.
"""

import unittest
import datetime
from decimal import Decimal
from typing import Dict, List, Optional

# 테스트 대상 모듈 import
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from payslip.work_time_processor import WorkTimeProcessor
from payslip.work_time_schema import WorkTimeSettings, AttendanceInputRecord, TimeCardInputRecord

class TestWorkTimeProcessor(unittest.TestCase):
    """WorkTimeProcessor 클래스의 기능을 테스트하는 테스트 케이스"""

    def setUp(self):
        """각 테스트 실행 전 설정"""
        # 테스트용 설정 생성
        self.test_settings: WorkTimeSettings = {
            "company_id": "TEST_COMP",
            "default_daily_scheduled_hours": Decimal("8.0"),
            "default_weekly_scheduled_hours": Decimal("40.0"),
            "overtime_rules": {},
            "night_work_rules": {},
            "holiday_rules": {},
            "break_time_rules": [],
            "attendance_status_codes": {
                "1": {"work_day_value": Decimal("1.0"), "is_paid_leave": False, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "정상근무"},
                "0": {"work_day_value": Decimal("0.0"), "is_paid_leave": False, "is_unpaid_leave": True, "counts_as_late": False, "counts_as_early_leave": False, "description": "무급결근"},
                "SICK_P": {"work_day_value": Decimal("1.0"), "is_paid_leave": True, "is_unpaid_leave": False, "counts_as_late": False, "counts_as_early_leave": False, "description": "유급병가"}
            }
        }
        
        # 테스트 대상 인스턴스 생성
        self.processor = WorkTimeProcessor(settings=self.test_settings)
        
        # 테스트 데이터 준비
        self.attendance_data: List[AttendanceInputRecord] = [
            {"date": "2025-05-01", "status_code": "1"},
            {"date": "2025-05-02", "status_code": "SICK_P"},
            {"date": "2025-05-03", "status_code": "0"}
        ]
        
        self.timecard_data: List[TimeCardInputRecord] = [
            {"date": "2025-05-01", "day_type": "weekday", "actual_clock_in": "09:00", "actual_clock_out": "18:00"}
        ]
        
        self.unknown_data = [{'date': '2025-01-01', 'random_key': 'value'}]
        self.empty_data = []

    def test_detect_mode_attendance(self):
        """출근 상태 기반 데이터 모드 감지 테스트"""
        mode = self.processor._detect_mode(self.attendance_data)
        self.assertEqual(mode, "attendance")

    def test_detect_mode_timecard(self):
        """출퇴근 시각 기반 데이터 모드 감지 테스트"""
        mode = self.processor._detect_mode(self.timecard_data)
        self.assertEqual(mode, "timecard")

    def test_detect_mode_unknown(self):
        """알 수 없는 형식 데이터 모드 감지 테스트"""
        mode = self.processor._detect_mode(self.unknown_data)
        self.assertEqual(mode, "unknown")

    def test_detect_mode_empty(self):
        """빈 데이터 모드 감지 테스트"""
        mode = self.processor._detect_mode(self.empty_data)
        self.assertEqual(mode, "unknown")

    def test_process_attendance_mode(self):
        """출근 상태 기반 모드 처리 테스트"""
        result = self.processor.process(
            input_data=self.attendance_data,
            period="2025-05",
            employee_id="EMP_TEST_ATT",
            mode="attendance"
        )
        
        # 기본 결과 검증
        self.assertEqual(result["processing_mode"], "attendance")
        self.assertEqual(result["employee_id"], "EMP_TEST_ATT")
        self.assertEqual(result["period"], "2025-05")
        self.assertIsNone(result["error"])
        
        # work_summary 검증 (실제 값은 AttendanceBasedCalculator 구현에 따라 달라질 수 있음)
        self.assertIsNotNone(result["work_summary"])
        
        # salary_basis 검증
        self.assertIsNotNone(result["salary_basis"])

    def test_process_timecard_mode(self):
        """출퇴근 시각 기반 모드 처리 테스트 (현재는 미구현 경고 예상)"""
        result = self.processor.process(
            input_data=self.timecard_data,
            period="2025-05",
            employee_id="EMP_TEST_TIME",
            mode="timecard"
        )
        
        # 기본 결과 검증
        self.assertEqual(result["processing_mode"], "timecard")
        self.assertEqual(result["employee_id"], "EMP_TEST_TIME")
        self.assertEqual(result["period"], "2025-05")
        
        # 현재 timecard 모드는 미구현이므로 경고 메시지 확인
        self.assertIn("Timecard mode (모드 B)는 아직 구현되지 않았습니다", result["warnings"][0])

    def test_process_auto_mode(self):
        """자동 모드 감지 처리 테스트"""
        result = self.processor.process(
            input_data=self.attendance_data,
            period="2025-05",
            employee_id="EMP_TEST_AUTO",
            mode="auto"
        )
        
        # 자동으로 attendance 모드로 감지되어야 함
        self.assertEqual(result["processing_mode"], "attendance")

    def test_process_empty_input(self):
        """빈 입력 처리 테스트 (오류 예상)"""
        result = self.processor.process(
            input_data=[],
            period="2025-05",
            employee_id="EMP_TEST_EMPTY"
        )
        
        # 오류 발생 확인
        self.assertEqual(result["processing_mode"], "error")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["error_code"], "INPUT_VALIDATION_ERROR")

    def test_process_unknown_mode_input(self):
        """알 수 없는 형식 입력 처리 테스트"""
        result = self.processor.process(
            input_data=self.unknown_data,
            period="2025-05",
            employee_id="EMP_TEST_UNKNOWN"
        )
        
        # 모드 감지 실패 시 'error' 모드로 처리되는지 확인
        self.assertEqual(result["processing_mode"], "error")
        self.assertIsNotNone(result["error"])
        self.assertEqual(result["error"]["error_code"], "MODE_DETECTION_FAILED")

if __name__ == '__main__':
    unittest.main()
