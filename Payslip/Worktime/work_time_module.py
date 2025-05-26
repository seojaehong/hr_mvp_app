"""
근로시간 자동 계산 모듈 - 근로시간 계산 모듈

이 파일은 일별/월별 근로시간 계산을 담당하는 WorkTimeCalculator 클래스를 구현합니다.
회사별 근로시간 정책, 휴일 정보 등을 고려하여 정규/연장/야간/휴일 근무시간을 계산합니다.
"""

import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional, Any

# 로깅 설정 (필요시)
import logging
logger = logging.getLogger(__name__)

class WorkTimeCalculator:
    def __init__(self, company_settings: dict = None):
        """
        근로시간 계산기 초기화.
        company_settings: 회사별 근로시간 정책, 휴일 정보 등을 담은 딕셔너리 (선택 사항)
        """
        self.company_settings = company_settings if company_settings else {}
        # 예시: 기본 휴게시간 정책, 연장근로 한도 등 설정 가능
        self.default_break_rules = self.company_settings.get("break_rules", [
            {"work_hours_threshold": 4, "break_minutes": 30},
            {"work_hours_threshold": 8, "break_minutes": 60}
        ])
        self.overtime_start_hour_weekday = self.company_settings.get("overtime_start_hour_weekday", 8) # 일 소정근로 8시간 초과 시 연장
        self.night_work_start_hour = self.company_settings.get("night_work_start_hour", 22) # 22시
        self.night_work_end_hour = self.company_settings.get("night_work_end_hour", 6) # 익일 06시

    def _parse_time(self, time_str: str) -> datetime.time | None:
        """HH:MM 형식의 시간 문자열을 datetime.time 객체로 변환"""
        if not time_str:
            return None
        try:
            return datetime.datetime.strptime(time_str, "%H:%M").time()
        except ValueError:
            logger.error(f"잘못된 시간 형식: {time_str}")
            return None

    def _calculate_duration_minutes(self, start_time: datetime.time, end_time: datetime.time, date: datetime.date, next_date: datetime.date) -> Decimal:
        """두 시간 사이의 기간을 분 단위로 계산 (익일 퇴근 고려)"""
        if not start_time or not end_time:
            return Decimal("0")

        start_dt = datetime.datetime.combine(date, start_time)
        end_dt = datetime.datetime.combine(date, end_time)

        if end_dt < start_dt: # 익일 퇴근의 경우
            end_dt = datetime.datetime.combine(next_date, end_time)
        
        duration = end_dt - start_dt
        return Decimal(duration.total_seconds() / 60)

    def calculate_daily_work_details(self, daily_record: dict) -> dict:
        """
        일별 근태 기록을 바탕으로 상세 근로시간(정규, 연장, 야간, 휴일)을 계산합니다.
        daily_record는 work_time_data_structure.md에 정의된 구조를 따릅니다.
        """
        # 초기화
        calculated_details = {
            "date": daily_record.get("date"),
            "regular_hours": Decimal("0"),
            "overtime_weekdays_1_5x": Decimal("0"),
            "overtime_holidays_1_5x": Decimal("0"),
            "overtime_holidays_2_0x": Decimal("0"),
            "night_hours": Decimal("0"),
            "holiday_work_hours_within_8": Decimal("0"),
            "holiday_work_hours_over_8": Decimal("0"),
            "actual_work_minutes_for_day": Decimal("0"), # 해당일 총 실근로 시간(분)
            "break_time_minutes_applied": Decimal(daily_record.get("break_time_minutes", 0)),
            "recognized_work_minutes": Decimal("0"), # 유급휴가 등 인정 시간 포함
            "warnings": []
        }

        # 필수 값 검증
        date_str = daily_record.get("date")
        actual_clock_in_str = daily_record.get("actual_clock_in")
        actual_clock_out_str = daily_record.get("actual_clock_out")
        shift_start_str = daily_record.get("shift_start_time", "09:00") # 기본값 또는 설정값 필요
        shift_end_str = daily_record.get("shift_end_time", "18:00")   # 기본값 또는 설정값 필요
        day_type = daily_record.get("day_type", "weekday")
        is_holiday_work_input = daily_record.get("is_holiday_work", False)
        leave_type = daily_record.get("leave_type")
        leave_hours_input = Decimal(daily_record.get("leave_hours", 0))

        if not all([date_str, actual_clock_in_str, actual_clock_out_str]):
            calculated_details["warnings"].append("필수 시간 정보(날짜, 출/퇴근) 누락")
            return calculated_details

        current_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        next_day_date = current_date + datetime.timedelta(days=1)
        
        actual_clock_in = self._parse_time(actual_clock_in_str)
        actual_clock_out = self._parse_time(actual_clock_out_str)
        shift_start_time = self._parse_time(shift_start_str)
        shift_end_time = self._parse_time(shift_end_str)

        if not actual_clock_in or not actual_clock_out or not shift_start_time or not shift_end_time:
            calculated_details["warnings"].append("시간 형식 오류")
            return calculated_details

        # 1. 총 체류 시간 및 실근로 시간 계산
        total_stay_minutes = self._calculate_duration_minutes(actual_clock_in, actual_clock_out, current_date, next_day_date)
        actual_work_minutes = total_stay_minutes - calculated_details["break_time_minutes_applied"]
        if actual_work_minutes < 0:
            actual_work_minutes = Decimal("0")
        calculated_details["actual_work_minutes_for_day"] = actual_work_minutes

        # 2. 유급 휴가 처리 (소정근로시간으로 인정)
        # 예시: 연차, 유급병가 등은 소정근로시간으로 인정. 반차는 4시간 인정 등.
        # 이 부분은 회사 정책 및 leave_type에 따라 상세 구현 필요
        recognized_leave_minutes = Decimal("0")
        if leave_type and "paid" in leave_type.lower() or leave_type == "annual" or "annual_half" in leave_type:
             recognized_leave_minutes = leave_hours_input * 60
        # 실제 근무가 없고 유급휴가만 있는 날 처리 (예: 전일 연차)
        if actual_work_minutes == 0 and recognized_leave_minutes > 0:
            # 소정근로시간만큼을 정규근로로 인정 (최대 8시간)
            # 이 부분은 소정근로시간을 알아야 함.
            daily_scheduled_minutes = self._calculate_duration_minutes(shift_start_time, shift_end_time, current_date, next_day_date) - self.company_settings.get("default_break_for_scheduled", 60)
            calculated_details["regular_hours"] = min(recognized_leave_minutes, daily_scheduled_minutes) / 60
            calculated_details["recognized_work_minutes"] = min(recognized_leave_minutes, daily_scheduled_minutes)
            return calculated_details
        
        # 실제 근무가 있는 경우, 인정 시간 합산
        calculated_details["recognized_work_minutes"] = actual_work_minutes + recognized_leave_minutes

        # --- 상세 시간 계산 로직 (정규, 연장, 야간, 휴일) --- 
        # 이 부분은 매우 복잡하며, 근로기준법 및 회사 정책을 정확히 반영해야 합니다.
        # 아래는 매우 간략화된 예시 로직이며, 실제 구현 시에는 훨씬 정교해야 합니다.

        # 소정근로시간 (분 단위)
        # shift_break_minutes = self._get_break_minutes_for_shift(shift_start_time, shift_end_time, current_date, next_day_date)
        # scheduled_work_minutes_net = self._calculate_duration_minutes(shift_start_time, shift_end_time, current_date, next_day_date) - shift_break_minutes
        # if scheduled_work_minutes_net < 0: scheduled_work_minutes_net = Decimal("0")

        # 임시: 일 소정근로시간 8시간(480분)으로 가정
        daily_scheduled_minutes_limit = Decimal(self.overtime_start_hour_weekday * 60)

        # 정규 근무 시간
        current_regular_minutes = min(actual_work_minutes, daily_scheduled_minutes_limit)
        calculated_details["regular_hours"] = current_regular_minutes / 60

        # 연장 근무 시간
        overtime_total_minutes = actual_work_minutes - current_regular_minutes
        if overtime_total_minutes < 0: overtime_total_minutes = Decimal("0")

        # 휴일 근무 여부 판단 (day_type과 is_holiday_work 조합)
        is_actual_holiday = (day_type in ["sunday", "public_holiday"] or is_holiday_work_input)

        if is_actual_holiday:
            # 휴일 근무 시: 8시간 이내는 1.5배, 8시간 초과는 2.0배
            holiday_work_within_8_hours_minutes = min(actual_work_minutes, daily_scheduled_minutes_limit)
            holiday_work_over_8_hours_minutes = actual_work_minutes - holiday_work_within_8_hours_minutes
            if holiday_work_over_8_hours_minutes < 0: holiday_work_over_8_hours_minutes = Decimal("0")
            
            calculated_details["holiday_work_hours_within_8"] = holiday_work_within_8_hours_minutes / 60
            calculated_details["holiday_work_hours_over_8"] = holiday_work_over_8_hours_minutes / 60
            # 휴일근무는 연장근무와 별개 또는 중복될 수 있음 (정책 확인 필요)
            # 여기서는 휴일근무가 연장근무보다 우선한다고 가정 (즉, 휴일에는 평일형 연장 X)
            calculated_details["overtime_holidays_1_5x"] = holiday_work_within_8_hours_minutes / 60 # 이름 변경 필요
            calculated_details["overtime_holidays_2_0x"] = holiday_work_over_8_hours_minutes / 60 # 이름 변경 필요
        elif day_type == "weekday" or day_type == "saturday": # 토요일도 평일 연장으로 볼 수 있음 (정책 확인)
            if overtime_total_minutes > 0:
                calculated_details["overtime_weekdays_1_5x"] = overtime_total_minutes / 60
        
        # 야간 근무 시간 (22:00 ~ 06:00)
        # 실제 근무 시간대와 야간 시간대의 교집합을 계산해야 함.
        # 이 로직은 start_time, end_time, date, next_date를 모두 고려해야 함.
        night_minutes = self._calculate_night_work_minutes(
            actual_clock_in, actual_clock_out, current_date, next_day_date
        )
        calculated_details["night_hours"] = night_minutes / 60

        # 소수점 처리 (예: 2자리까지 반올림)
        for key in ["regular_hours", "overtime_weekdays_1_5x", "overtime_holidays_1_5x", "overtime_holidays_2_0x", "night_hours", "holiday_work_hours_within_8", "holiday_work_hours_over_8"]:
            if isinstance(calculated_details[key], Decimal):
                calculated_details[key] = calculated_details[key].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            else:
                 calculated_details[key] = Decimal(str(calculated_details[key])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return calculated_details

    def _calculate_night_work_minutes(self, start_time: datetime.time, end_time: datetime.time, 
                                     date: datetime.date, next_date: datetime.date) -> Decimal:
        """야간 근무 시간(22:00~06:00)을 계산합니다."""
        if not start_time or not end_time:
            return Decimal("0")
        
        # 야간 시간대 설정
        night_start_hour = self.night_work_start_hour  # 22시
        night_end_hour = self.night_work_end_hour      # 익일 06시
        
        night_start_time = datetime.time(night_start_hour, 0)
        night_end_time = datetime.time(night_end_hour, 0)
        
        # 근무 시작/종료 datetime 객체
        work_start_dt = datetime.datetime.combine(date, start_time)
        work_end_dt = datetime.datetime.combine(date, end_time)
        if work_end_dt < work_start_dt:  # 익일 퇴근
            work_end_dt = datetime.datetime.combine(next_date, end_time)
        
        # 당일 야간 시간대
        night_start_dt = datetime.datetime.combine(date, night_start_time)
        night_end_dt = datetime.datetime.combine(next_date, night_end_time)
        
        # 야간 근무 시간 계산 (교집합)
        night_minutes = Decimal("0")
        
        # 야간 시간대와 근무 시간대의 교집합 계산
        if work_end_dt > night_start_dt and work_start_dt < night_end_dt:
            overlap_start = max(work_start_dt, night_start_dt)
            overlap_end = min(work_end_dt, night_end_dt)
            
            if overlap_end > overlap_start:
                night_minutes = Decimal((overlap_end - overlap_start).total_seconds() / 60)
        
        return night_minutes

    def calculate_monthly_work_hours(self, employee_id: str, timecard_data: list[dict], period_start_date_str: str, period_end_date_str: str) -> dict:
        """
        월별 총 근로시간을 집계합니다.
        timecard_data: 해당 직원의 해당 월 일별 근태 기록 리스트
        """
        monthly_summary = {
            "employee_id": employee_id,
            "period_start_date": period_start_date_str,
            "period_end_date": period_end_date_str,
            "total_work_days": 0,
            "total_paid_leave_days": Decimal("0"),
            "summary_hours": {
                "total_scheduled_hours": Decimal("0"),
                "total_actual_work_hours": Decimal("0"),
                "total_recognized_work_hours": Decimal("0"),
                "total_break_time_hours": Decimal("0")
            },
            "detailed_hours": {
                "regular_hours": Decimal("0"),
                "overtime_hours": {
                    "weekdays_1_5x": Decimal("0"),
                    "weekdays_2_0x": Decimal("0"),
                    "holidays_1_5x": Decimal("0"),
                    "holidays_2_0x": Decimal("0")
                },
                "night_hours": Decimal("0"),
                "holiday_hours": {
                    "paid_holiday_work_hours_within_8": Decimal("0"),
                    "paid_holiday_work_hours_over_8": Decimal("0"),
                    "unpaid_holiday_work_hours": Decimal("0")
                }
            },
            "exceptions_summary": [], # 상세 구현 필요
            "daily_records_processed": [],
            "warnings": []
        }

        for daily_record in timecard_data:
            # 기간 필터링 (선택적, 이미 필터링된 데이터가 올 수도 있음)
            record_date = datetime.datetime.strptime(daily_record["date"], "%Y-%m-%d").date()
            period_start = datetime.datetime.strptime(period_start_date_str, "%Y-%m-%d").date()
            period_end = datetime.datetime.strptime(period_end_date_str, "%Y-%m-%d").date()
            if not (period_start <= record_date <= period_end):
                continue

            daily_calculated = self.calculate_daily_work_details(daily_record)
            monthly_summary["daily_records_processed"].append(daily_calculated)
            if daily_calculated.get("warnings"):
                monthly_summary["warnings"].extend(daily_calculated["warnings"])

            # 합산 로직
            if daily_calculated["actual_work_minutes_for_day"] > 0 or daily_calculated["recognized_work_minutes"] > 0 :
                 monthly_summary["total_work_days"] += 1 # 실근무 또는 유급휴가일
            
            # 예시: 유급 반차(4시간)는 0.5일로 계산
            if daily_record.get("leave_hours",0) > 0 and ("paid" in daily_record.get("leave_type","").lower() or "annual" in daily_record.get("leave_type","").lower()):
                if daily_record.get("leave_hours") == 4: # 간단한 예시
                    monthly_summary["total_paid_leave_days"] += Decimal("0.5")
                elif daily_record.get("leave_hours") >= 8:
                    monthly_summary["total_paid_leave_days"] += Decimal("1.0")
                # 기타 시간 단위 휴가 처리 필요

            monthly_summary["summary_hours"]["total_actual_work_hours"] += daily_calculated["actual_work_minutes_for_day"] / 60
            monthly_summary["summary_hours"]["total_recognized_work_hours"] += daily_calculated["recognized_work_minutes"] / 60
            monthly_summary["summary_hours"]["total_break_time_hours"] += daily_calculated["break_time_minutes_applied"] / 60
            # total_scheduled_hours는 별도 계산 필요 (근무일 기반)

            monthly_summary["detailed_hours"]["regular_hours"] += daily_calculated["regular_hours"]
            monthly_summary["detailed_hours"]["overtime_hours"]["weekdays_1_5x"] += daily_calculated["overtime_weekdays_1_5x"]
            monthly_summary["detailed_hours"]["overtime_hours"]["holidays_1_5x"] += daily_calculated["overtime_holidays_1_5x"]
            monthly_summary["detailed_hours"]["overtime_hours"]["holidays_2_0x"] += daily_calculated["overtime_holidays_2_0x"]
            monthly_summary["detailed_hours"]["night_hours"] += daily_calculated["night_hours"]
            monthly_summary["detailed_hours"]["holiday_hours"]["paid_holiday_work_hours_within_8"] += daily_calculated["holiday_work_hours_within_8"]
            monthly_summary["detailed_hours"]["holiday_hours"]["paid_holiday_work_hours_over_8"] += daily_calculated["holiday_work_hours_over_8"]

        # 최종 소수점 처리
        for cat_key, cat_val in monthly_summary["detailed_hours"].items():
            if isinstance(cat_val, Decimal):
                monthly_summary["detailed_hours"][cat_key] = cat_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif isinstance(cat_val, dict): # overtime_hours, holiday_hours
                for sub_key, sub_val in cat_val.items():
                    if isinstance(sub_val, Decimal):
                         monthly_summary["detailed_hours"][cat_key][sub_key] = sub_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        
        for sum_key, sum_val in monthly_summary["summary_hours"].items():
            if isinstance(sum_val, Decimal):
                monthly_summary["summary_hours"][sum_key] = sum_val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return monthly_summary

# 사용 예시 (테스트용)
if __name__ == '__main__':
    calculator = WorkTimeCalculator()
    sample_timecard_emp1 = [
        {
            "date": "2025-07-01", "day_type": "weekday", "shift_start_time": "09:00", "shift_end_time": "18:00",
            "actual_clock_in": "08:50", "actual_clock_out": "20:30", "break_time_minutes": 60, "is_holiday_work": False,
            "leave_type": None, "leave_hours": 0, "notes": "야근"
        },
        {
            "date": "2025-07-02", "day_type": "weekday", "shift_start_time": "09:00", "shift_end_time": "18:00",
            "actual_clock_in": "09:00", "actual_clock_out": "13:00", "break_time_minutes": 0,
            "is_holiday_work": False, "leave_type": "annual_half_day_pm", "leave_hours": 4, "notes": "오후 반차"
        },
        {
            "date": "2025-07-03", "day_type": "weekday", "shift_start_time": "09:00", "shift_end_time": "18:00",
            "actual_clock_in": "00:00", "actual_clock_out": "00:00", "break_time_minutes": 0, # 실제 근무 없음
            "is_holiday_work": False, "leave_type": "annual_full_day", "leave_hours": 8, "notes": "전일 연차"
        },
         {
            "date": "2025-07-06", "day_type": "sunday", "shift_start_time": "09:00", "shift_end_time": "18:00",
            "actual_clock_in": "10:00", "actual_clock_out": "19:30", "break_time_minutes": 60, # 8시간 초과 근무로 1시간 휴게 가정
            "is_holiday_work": True, "leave_type": None, "leave_hours": 0, "notes": "일요일 특근 8.5시간"
        }
    ]

    print("--- 일별 계산 결과 ---")
    for record in sample_timecard_emp1:
        daily_result = calculator.calculate_daily_work_details(record)
        print(f"날짜: {daily_result['date']}, 정규: {daily_result['regular_hours']}시간, 연장: {daily_result['overtime_weekdays_1_5x']}시간, 휴일: {daily_result['holiday_work_hours_within_8']}시간")
    
    print("\n--- 월별 집계 결과 ---")
    monthly_result = calculator.calculate_monthly_work_hours(
        "EMP001", sample_timecard_emp1, "2025-07-01", "2025-07-31"
    )
    print(f"총 근무일수: {monthly_result['total_work_days']}")
    print(f"총 실근로시간: {monthly_result['summary_hours']['total_actual_work_hours']}시간")
    print(f"정규근로: {monthly_result['detailed_hours']['regular_hours']}시간")
    print(f"연장근로(평일): {monthly_result['detailed_hours']['overtime_hours']['weekdays_1_5x']}시간")
    print(f"휴일근로: {monthly_result['detailed_hours']['holiday_hours']['paid_holiday_work_hours_within_8']}시간")
