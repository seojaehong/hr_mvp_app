"""
근로시간 자동 계산 모듈 - 출결 기반 계산기 (모드 A)

이 파일은 출결 상태 코드 기반 근무일수 계산기를 구현합니다.
AttendanceInputData를 입력받아 근무일수, 유급/무급 휴가 등을 계산합니다.
"""

import logging
import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP

from .schema import (
    AttendanceInputRecord, AttendanceSummary, SalaryBasis, ErrorDetails, 
    WorkTimeCalculationResult
)

# 로깅 설정
logger = logging.getLogger(__name__)

class AttendanceBasedCalculator:
    """
    출결 상태 코드 기반 (모드 A) 근무일수 계산기입니다.
    AttendanceInputData를 입력받아 근무일수, 유급/무급 휴가 등을 계산합니다.
    """

    def __init__(self, settings: Dict[str, Any]):
        """
        AttendanceBasedCalculator 초기화.

        Args:
            settings: 회사별 및 모듈 운영 설정을 담은 딕셔너리.
                      특히 `attendance_status_codes` 정의가 중요합니다.
        """
        self.settings = settings
        self.status_codes_map = settings.get("attendance_status_codes", {})
        logger.info("AttendanceBasedCalculator initialized.")

    def _get_status_code_details(self, status_code: str) -> Dict[str, Any]:
        """
        출결 상태 코드에 대한 상세 정보를 반환합니다.

        Args:
            status_code: 출결 상태 코드

        Returns:
            Dict[str, Any]: 상태 코드 상세 정보
        """
        # 기본값
        default_details = {
            "work_day_value": Decimal("0.0"),
            "is_paid_leave": False,
            "is_unpaid_leave": False,
            "counts_as_late": False,
            "counts_as_early_leave": False,
            "description": "Unknown status code"
        }
        
        # 설정에서 상태 코드 정보 조회
        if status_code in self.status_codes_map:
            return self.status_codes_map[status_code]
        
        # 기본 상태 코드 매핑 (설정에 없는 경우)
        basic_mapping = {
            "1": {"work_day_value": Decimal("1.0"), "description": "정상 출근"},
            "2": {"work_day_value": Decimal("0.0"), "is_unpaid_leave": True, "description": "결근"},
            "3": {"work_day_value": Decimal("1.0"), "is_paid_leave": True, "description": "유급 휴가"},
            "4": {"work_day_value": Decimal("0.0"), "is_unpaid_leave": True, "description": "무급 휴가"},
            "5": {"work_day_value": Decimal("0.5"), "description": "반차", "counts_as_early_leave": True},
            "L": {"work_day_value": Decimal("1.0"), "description": "지각", "counts_as_late": True},
            "E": {"work_day_value": Decimal("1.0"), "description": "조퇴", "counts_as_early_leave": True}
        }
        
        if status_code in basic_mapping:
            return {**default_details, **basic_mapping[status_code]}
        
        logger.warning(f"Unknown status code: {status_code}")
        return default_details

    def _get_period_dates(self, period: str) -> tuple:
        """
        기간 문자열(YYYY-MM)에서 시작일과 종료일을 계산합니다.

        Args:
            period: 기간 문자열 (예: "2025-05")

        Returns:
            tuple: (시작일, 종료일, 총 일수)
        """
        try:
            year, month = map(int, period.split("-"))
            start_date = datetime.date(year, month, 1)
            
            # 월의 마지막 날 계산
            if month == 12:
                next_month = datetime.date(year + 1, 1, 1)
            else:
                next_month = datetime.date(year, month + 1, 1)
            
            end_date = next_month - datetime.timedelta(days=1)
            total_days = (end_date - start_date).days + 1
            
            return start_date, end_date, total_days
        
        except ValueError as e:
            logger.error(f"Invalid period format: {period}")
            raise ValueError(f"Invalid period format: {period}. Expected YYYY-MM.") from e

    def _count_scheduled_work_days(self, start_date: datetime.date, end_date: datetime.date) -> int:
        """
        기간 내 예정된 근무일수를 계산합니다. (주말 제외)

        Args:
            start_date: 시작일
            end_date: 종료일

        Returns:
            int: 예정된 근무일수
        """
        work_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # 0=월요일, 5=토요일, 6=일요일
            if current_date.weekday() < 5:  # 월~금요일
                work_days += 1
            
            current_date += datetime.timedelta(days=1)
        
        return work_days

    def calculate(self, records: List[AttendanceInputRecord], 
                 options: Dict[str, Any]) -> Dict[str, Any]:
        """
        출결 기반 근무일수 계산을 실행합니다.

        Args:
            records: 출결 기록 리스트
            options: 추가 옵션 (period, employee_id 등)

        Returns:
            Dict[str, Any]: 계산 결과
        """
        period = options.get("period", "")
        employee_id = options.get("employee_id")
        
        logger.info(f"Starting attendance calculation for employee: {employee_id}, period: {period}")
        
        result = {
            "attendance_summary": None,
            "salary_basis": None,
            "warnings": []
        }
        
        try:
            # 기간 정보 계산
            start_date, end_date, total_days = self._get_period_dates(period)
            scheduled_work_days = self._count_scheduled_work_days(start_date, end_date)
            
            # 초기화
            attendance_summary = AttendanceSummary(
                total_days_in_period=total_days,
                scheduled_work_days=scheduled_work_days,
                actual_work_days=Decimal("0"),
                full_work_days=0,
                partial_work_day_ratios=[],
                absent_days=0,
                paid_leave_days=Decimal("0"),
                unpaid_leave_days=Decimal("0"),
                late_count=0,
                early_leave_count=0
            )
            
            # 날짜별 출결 상태 매핑
            date_status_map = {record.date: record for record in records}
            
            # 각 날짜별 처리
            current_date = start_date
            while current_date <= end_date:
                # 해당 날짜의 출결 기록이 있는 경우
                if current_date in date_status_map:
                    record = date_status_map[current_date]
                    status_details = self._get_status_code_details(record.status_code)
                    
                    # 근무일 가치 (1.0=전일, 0.5=반일, 0.0=결근)
                    work_day_value = Decimal(str(status_details.get("work_day_value", "0")))
                    
                    # 부분 근무일 처리 (worked_minutes가 있는 경우)
                    if record.worked_minutes is not None and record.worked_minutes > 0:
                        # 일 소정근로시간 (분)
                        daily_minutes = Decimal(self.settings.get("daily_work_minutes_standard", 480))
                        
                        # 부분 근무일 비율 계산
                        work_ratio = min(Decimal(str(record.worked_minutes)) / daily_minutes, Decimal("1.0"))
                        # work_day_value = work_ratio
                        
                        # 부분 근무일 비율 기록
                        if work_ratio > Decimal("0") and work_ratio < Decimal("1.0"):
                            attendance_summary.partial_work_day_ratios.append(work_ratio)
                    
                    # 근무일 집계
                    attendance_summary.actual_work_days += work_day_value
                    
                    # 전일 근무
                    if work_day_value == Decimal("1.0"):
                        attendance_summary.full_work_days += 1
                    
                    # 결근
                    if work_day_value == Decimal("0.0") and not status_details.get("is_paid_leave") and not status_details.get("is_unpaid_leave"):
                        attendance_summary.absent_days += 1
                    
                    # 유급 휴가
                    if status_details.get("is_paid_leave"):
                        attendance_summary.paid_leave_days += work_day_value
                    
                    # 무급 휴가
                    if status_details.get("is_unpaid_leave"):
                        attendance_summary.unpaid_leave_days += work_day_value
                    
                    # 지각
                    if status_details.get("counts_as_late"):
                        attendance_summary.late_count += 1
                    
                    # 조퇴
                    if status_details.get("counts_as_early_leave"):
                        attendance_summary.early_leave_count += 1
                
                # 다음 날짜로
                current_date += datetime.timedelta(days=1)
            
            # 급여 계산 기초 정보
            salary_basis = SalaryBasis(
                payment_target_days=attendance_summary.actual_work_days + attendance_summary.paid_leave_days,
                deduction_days=attendance_summary.absent_days + attendance_summary.unpaid_leave_days
            )
            
            # 소수점 처리 (2자리까지 반올림)
            attendance_summary.actual_work_days = attendance_summary.actual_work_days.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            attendance_summary.paid_leave_days = attendance_summary.paid_leave_days.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            attendance_summary.unpaid_leave_days = attendance_summary.unpaid_leave_days.quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            
            # 결과 설정
            result["attendance_summary"] = attendance_summary
            result["salary_basis"] = salary_basis
            
            # 경고 처리
            if attendance_summary.absent_days > 0:
                result["warnings"].append(f"결근일 감지: {attendance_summary.absent_days}일")
            
            if attendance_summary.late_count > 0:
                result["warnings"].append(f"지각 감지: {attendance_summary.late_count}회")
            
            if attendance_summary.early_leave_count > 0:
                result["warnings"].append(f"조퇴 감지: {attendance_summary.early_leave_count}회")
            
        except Exception as e:
            logger.error(f"Error in attendance calculation: {str(e)}", exc_info=True)
            result["error"] = ErrorDetails(
                error_code="CALCULATION_ERROR",
                message=f"Error during calculation: {str(e)}",
                details=str(e)
            )
        
        return result
