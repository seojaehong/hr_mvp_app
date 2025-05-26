"""
근로시간 자동 계산 모듈 - 타임카드 기반 계산기 (모드 B)

이 파일은 출퇴근 시각 기반 근로시간 계산기를 구현합니다.
TimeCardInputData를 입력받아 정규, 연장, 야간, 휴일 근무시간 등을 계산합니다.
"""

import logging
import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal, ROUND_HALF_UP

from .schema import (
    TimeCardInputData,
    TimeCardRecord,
    TimeSummary,
    WorkTimeCalculationResult,
    ErrorDetails,
    ComplianceAlert,
    WorkDayDetail
)
from .processor import BaseCalculator

# 로깅 설정
logger = logging.getLogger(__name__)

class TimeCardBasedCalculator(BaseCalculator):
    """
    출퇴근 시각 기반 (모드 B) 근로시간 계산기입니다.
    TimeCardInputData를 입력받아 정규, 연장, 야간, 휴일 근무시간 등을 계산합니다.
    """

    def __init__(self, settings: Dict[str, Any]):
        """
        TimeCardBasedCalculator 초기화.

        Args:
            settings: 회사별 및 모듈 운영 설정을 담은 딕셔너리.
        """
        super().__init__(settings)
        self.company_settings = settings.get("company_settings", {})
        self.minimum_wages_config = settings.get("minimum_wages_config", {})
        self.holidays_config = settings.get("holidays_config", {})
        logger.info("TimeCardBasedCalculator initialized.")

    def _parse_time(self, time_str: str) -> datetime.time:
        """
        HH:MM 형식의 시간 문자열을 datetime.time 객체로 변환합니다.

        Args:
            time_str: HH:MM 형식의 시간 문자열

        Returns:
            datetime.time: 변환된 시간 객체
        """
        try:
            return datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError as e:
            logger.error(f"Invalid time format: {time_str}")
            raise ValueError(f"Invalid time format: {time_str}") from e

    def _calculate_duration_minutes(self, start_time: datetime.time, end_time: datetime.time, 
                                   date: datetime.date, next_date: datetime.date) -> Decimal:
        """
        두 시간 사이의 기간을 분 단위로 계산합니다. (익일 퇴근 고려)

        Args:
            start_time: 시작 시간
            end_time: 종료 시간
            date: 기준 날짜
            next_date: 다음 날짜 (익일 퇴근 고려)

        Returns:
            Decimal: 분 단위 기간
        """
        start_dt = datetime.datetime.combine(date, start_time)
        end_dt = datetime.datetime.combine(date, end_time)

        if end_dt < start_dt:  # 익일 퇴근의 경우
            end_dt = datetime.datetime.combine(next_date, end_time)
        
        duration = end_dt - start_dt
        return Decimal(duration.total_seconds() / 60)

    def _get_break_minutes(self, work_minutes: Decimal) -> Decimal:
        """
        근로시간에 따른 법정 휴게시간을 계산합니다.

        Args:
            work_minutes: 총 근로시간 (분)

        Returns:
            Decimal: 법정 휴게시간 (분)
        """
        break_rules = self.company_settings.get("break_time_rules", [
            {"threshold_minutes": 240, "break_minutes": 30},  # 4시간 이상 근무 시 30분 휴게
            {"threshold_minutes": 480, "break_minutes": 60}   # 8시간 이상 근무 시 60분 휴게
        ])
        
        # 규칙을 내림차순으로 정렬 (더 긴 근로시간 기준을 먼저 적용)
        sorted_rules = sorted(break_rules, key=lambda x: x["threshold_minutes"], reverse=True)
        
        for rule in sorted_rules:
            if work_minutes >= Decimal(rule["threshold_minutes"]):
                return Decimal(rule["break_minutes"])
        
        return Decimal("0")

    def _is_holiday(self, date: datetime.date) -> bool:
        """
        해당 날짜가 휴일인지 확인합니다.

        Args:
            date: 확인할 날짜

        Returns:
            bool: 휴일 여부
        """
        # 일요일 확인
        if date.weekday() == 6:  # 0=월요일, 6=일요일
            return True
        
        # 공휴일 확인 (holidays_config가 있는 경우)
        if self.holidays_config:
            holidays = self.holidays_config.get("holidays", [])
            for holiday in holidays:
                holiday_date = holiday.get("date")
                if isinstance(holiday_date, str):
                    holiday_date = datetime.datetime.strptime(holiday_date, "%Y-%m-%d").date()
                if holiday_date == date:
                    return True
        
        return False

    def _calculate_daily_work_details(self, record: TimeCardRecord, date_idx: int) -> WorkDayDetail:
        """
        일별 근태 기록을 바탕으로 상세 근로시간을 계산합니다.

        Args:
            record: 일별 근태 기록
            date_idx: 날짜 인덱스 (익일 계산용)

        Returns:
            WorkDayDetail: 일별 근로시간 상세 정보
        """
        # 초기화
        result = WorkDayDetail(
            date=record.date,
            regular_hours=Decimal("0"),
            overtime_hours=Decimal("0"),
            night_hours=Decimal("0"),
            holiday_hours=Decimal("0"),
            holiday_overtime_hours=Decimal("0"),
            actual_work_minutes=Decimal("0"),
            break_minutes_applied=Decimal(record.break_time_minutes or 0),
            warnings=[]
        )

        try:
            # 시간 파싱
            start_time = self._parse_time(record.start_time)
            end_time = self._parse_time(record.end_time)
            
            # 다음 날짜 계산 (익일 퇴근 고려)
            next_date = record.date + datetime.timedelta(days=1)
            
            # 총 체류 시간 계산
            total_stay_minutes = self._calculate_duration_minutes(start_time, end_time, record.date, next_date)
            
            # 휴게시간 자동 계산 (설정된 휴게시간이 없는 경우)
            if not record.break_time_minutes:
                auto_break_minutes = self._get_break_minutes(total_stay_minutes)
                result.break_minutes_applied = auto_break_minutes
                result.warnings.append(f"휴게시간이 지정되지 않아 자동 계산됨: {auto_break_minutes}분")
            
            # 실근로 시간 계산
            actual_work_minutes = total_stay_minutes - result.break_minutes_applied
            if actual_work_minutes < 0:
                actual_work_minutes = Decimal("0")
                result.warnings.append("휴게시간이 총 체류시간보다 큽니다. 실근로시간을 0으로 설정합니다.")
            
            result.actual_work_minutes = actual_work_minutes
            
            # 일 소정근로시간 (분)
            daily_regular_minutes = Decimal(self.company_settings.get("daily_work_minutes_standard", 480))
            
            # 휴일 여부 확인
            is_holiday = self._is_holiday(record.date)
            
            if is_holiday:
                # 휴일 근무 처리
                holiday_work_within_8_hours = min(actual_work_minutes, daily_regular_minutes)
                holiday_work_over_8_hours = max(Decimal("0"), actual_work_minutes - daily_regular_minutes)
                
                result.holiday_hours = holiday_work_within_8_hours / 60
                result.holiday_overtime_hours = holiday_work_over_8_hours / 60
                
                # 휴일 근무 경고
                if actual_work_minutes > 0:
                    result.warnings.append(f"휴일 근무 감지: {actual_work_minutes / 60:.2f}시간")
            else:
                # 평일 근무 처리
                regular_minutes = min(actual_work_minutes, daily_regular_minutes)
                overtime_minutes = max(Decimal("0"), actual_work_minutes - daily_regular_minutes)
                
                result.regular_hours = regular_minutes / 60
                result.overtime_hours = overtime_minutes / 60
                
                # 연장 근무 경고
                if overtime_minutes > 0:
                    result.warnings.append(f"연장 근무 감지: {overtime_minutes / 60:.2f}시간")
            
            # 야간 근무 시간 계산 (22:00-06:00)
            # 이 부분은 복잡하므로 간략화된 구현입니다.
            # 실제 구현에서는 시간대 교차 계산이 더 정교해야 합니다.
            night_start = self._parse_time(self.company_settings.get("night_shift_start_time", "22:00"))
            night_end = self._parse_time(self.company_settings.get("night_shift_end_time", "06:00"))
            
            # 야간 근무 시간 계산 로직 (간략화)
            night_minutes = Decimal("0")
            
            # 시작 시간이 야간 시간대에 있는 경우
            if (start_time >= night_start) or (start_time <= night_end and end_time > start_time):
                # 야간 근무 감지 (상세 계산은 실제 구현에서 더 정교하게)
                result.warnings.append("야간 근무 감지됨. 상세 계산 필요.")
                
                # 간략화된 야간 근무 시간 계산 (예시)
                night_minutes = Decimal("60")  # 임시값
            
            result.night_hours = night_minutes / 60
            
            # 소수점 처리 (2자리까지 반올림)
            for key in ["regular_hours", "overtime_hours", "night_hours", "holiday_hours", "holiday_overtime_hours"]:
                value = getattr(result, key)
                setattr(result, key, value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            
        except Exception as e:
            logger.error(f"Error calculating daily work details: {str(e)}", exc_info=True)
            result.warnings.append(f"계산 오류: {str(e)}")
        
        return result

    def calculate(self, input_data: TimeCardInputData) -> Dict[str, Any]:
        """
        타임카드 기반 근로시간 계산을 실행합니다.

        Args:
            input_data: 타임카드 입력 데이터

        Returns:
            Dict[str, Any]: 계산 결과
        """
        logger.info(f"Starting timecard calculation for employee: {input_data.employee_id}, period: {input_data.period}")
        
        result = {
            "time_summary": TimeSummary(),
            "daily_details": [],
            "warnings": []
        }
        
        try:
            # 입력 데이터 검증
            if not input_data.records:
                result["error"] = ErrorDetails(
                    error_code="EMPTY_RECORDS",
                    message="No timecard records provided"
                )
                return result
            
            # 일별 계산
            for idx, record in enumerate(input_data.records):
                daily_detail = self._calculate_daily_work_details(record, idx)
                result["daily_details"].append(daily_detail)
                result["warnings"].extend(daily_detail.warnings)
            
            # 월별 집계
            time_summary = TimeSummary()
            
            for detail in result["daily_details"]:
                time_summary.regular_hours += detail.regular_hours
                time_summary.overtime_hours += detail.overtime_hours
                time_summary.night_hours += detail.night_hours
                time_summary.holiday_hours += detail.holiday_hours
                time_summary.holiday_overtime_hours += detail.holiday_overtime_hours
            
            # 총 실근로시간 계산
            total_net_work_hours = Decimal("0")
            for detail in result["daily_details"]:
                total_net_work_hours += detail.actual_work_minutes / 60
            
            time_summary.total_net_work_hours = total_net_work_hours.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # 소수점 처리 (2자리까지 반올림)
            for key in ["regular_hours", "overtime_hours", "night_hours", "holiday_hours", "holiday_overtime_hours"]:
                value = getattr(time_summary, key)
                setattr(time_summary, key, value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
            
            result["time_summary"] = time_summary
            
            # 컴플라이언스 검사
            self._check_compliance(result, input_data)
            
        except Exception as e:
            logger.error(f"Error in timecard calculation: {str(e)}", exc_info=True)
            result["error"] = ErrorDetails(
                error_code="CALCULATION_ERROR",
                message=f"Error during calculation: {str(e)}",
                details=str(e)
            )
        
        return result

    def _check_compliance(self, result: Dict[str, Any], input_data: TimeCardInputData) -> None:
        """
        근로시간 관련 법적 컴플라이언스를 검사합니다.

        Args:
            result: 계산 결과
            input_data: 입력 데이터
        """
        compliance_alerts = []
        
        # 주간 연장근로 한도 검사 (52시간)
        weekly_limit_minutes = Decimal(self.company_settings.get("weekly_work_minutes_standard", 2400))
        weekly_limit_buffer = Decimal(self.company_settings.get("weekly_overtime_limit_buffer", 720))  # 12시간
        
        # 주별 근로시간 집계 (간략화된 구현)
        # 실제 구현에서는 날짜를 기준으로 주차를 정확히 계산해야 함
        weekly_work_minutes = {}
        
        for detail in result["daily_details"]:
            # 임시로 날짜의 주차를 계산 (간략화)
            week_num = detail.date.isocalendar()[1]
            
            if week_num not in weekly_work_minutes:
                weekly_work_minutes[week_num] = Decimal("0")
            
            weekly_work_minutes[week_num] += detail.actual_work_minutes
        
        # 주간 한도 초과 검사
        for week_num, minutes in weekly_work_minutes.items():
            if minutes > (weekly_limit_minutes + weekly_limit_buffer):
                compliance_alerts.append(ComplianceAlert(
                    alert_code="EXCESSIVE_WEEKLY_WORK",
                    message=f"{week_num}주차 근로시간이 주 52시간을 초과합니다: {minutes / 60:.2f}시간",
                    severity="error",
                    details={"week": week_num, "hours": float(minutes / 60)}
                ))
        
        # 일 연속 근로시간 검사 (휴게시간 부족)
        for detail in result["daily_details"]:
            if detail.actual_work_minutes > Decimal("240") and detail.break_minutes_applied < Decimal("30"):
                compliance_alerts.append(ComplianceAlert(
                    alert_code="INSUFFICIENT_BREAK_TIME",
                    message=f"{detail.date} 4시간 이상 근무에 필요한 최소 휴게시간(30분)이 부족합니다",
                    severity="warning",
                    details={"date": str(detail.date), "break_minutes": float(detail.break_minutes_applied)}
                ))
            
            if detail.actual_work_minutes > Decimal("480") and detail.break_minutes_applied < Decimal("60"):
                compliance_alerts.append(ComplianceAlert(
                    alert_code="INSUFFICIENT_BREAK_TIME",
                    message=f"{detail.date} 8시간 이상 근무에 필요한 최소 휴게시간(60분)이 부족합니다",
                    severity="error",
                    details={"date": str(detail.date), "break_minutes": float(detail.break_minutes_applied)}
                ))
        
        # 결과에 컴플라이언스 알림 추가
        result["compliance_alerts"] = compliance_alerts
