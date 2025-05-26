"""
근로시간 자동 계산 모듈 - 스키마 정의 (Pydantic BaseModel 사용)

이 파일은 근로시간 계산기의 공통 입출력 데이터 구조, 오류 형식 등을 정의합니다.
Pydantic 모델을 사용하여 데이터 유효성 검증 및 명확한 구조를 제공합니다.
"""

from typing import List, Optional, Dict, Any, Literal
from decimal import Decimal
import datetime
import re
from pydantic import BaseModel, Field, field_validator, RootModel

# --- 기본 구성 요소 --- #

class WorkDayDetail(BaseModel):
    """모드 B (TimeCardBased)에서 일별 계산 상세 결과"""
    date: datetime.date
    regular_hours: Decimal = Field(default=Decimal("0.0"))
    overtime_hours: Decimal = Field(default=Decimal("0.0"))
    night_hours: Decimal = Field(default=Decimal("0.0"))
    holiday_hours: Decimal = Field(default=Decimal("0.0"))
    holiday_overtime_hours: Decimal = Field(default=Decimal("0.0"))
    actual_work_minutes: Decimal = Field(default=Decimal("0.0"))
    break_minutes_applied: Decimal = Field(default=Decimal("0.0"))
    warnings: List[str] = Field(default_factory=list)

# --- 공통 출력 포맷 정의 --- #

class AttendanceSummary(BaseModel):
    """출근 상태 기반 (모드 A) 작업 요약"""
    total_days_in_period: int
    scheduled_work_days: int
    actual_work_days: Decimal # full_work_days + sum(partial_work_day_ratios)
    full_work_days: int = Field(default=0)
    partial_work_day_ratios: List[Decimal] = Field(default_factory=list)
    absent_days: int = Field(default=0)
    paid_leave_days: Decimal = Field(default=Decimal("0.0"))
    unpaid_leave_days: Decimal = Field(default=Decimal("0.0"))
    late_count: int = Field(default=0)
    early_leave_count: int = Field(default=0)

class TimeSummary(BaseModel):
    """시간 기록 기반 (모드 B) 상세 시간 요약"""
    regular_hours: Decimal = Field(default=Decimal("0.0"))
    overtime_hours: Decimal = Field(default=Decimal("0.0"))
    night_hours: Decimal = Field(default=Decimal("0.0"))
    holiday_hours: Decimal = Field(default=Decimal("0.0"))
    holiday_overtime_hours: Decimal = Field(default=Decimal("0.0"))
    total_net_work_hours: Decimal = Field(default=Decimal("0.0"))
    # 아래 필드들은 필요시 유지 또는 total_net_work_hours로 통합 검토
    # total_recognized_work_hours: Optional[Decimal] = None
    # total_actual_work_hours: Optional[Decimal] = None
    # total_scheduled_hours: Optional[Decimal] = None
    # total_break_time_hours: Optional[Decimal] = None
    # overtime_details: Optional[Dict[str, Decimal]] = None
    # holiday_details: Optional[Dict[str, Decimal]] = None

class SalaryBasis(BaseModel):
    """급여 계산 기초 정보"""
    base_salary_for_period: Optional[Decimal] = None
    payment_target_days: Optional[Decimal] = None
    deduction_days: Optional[Decimal] = None

class ErrorDetails(BaseModel):
    """오류 발생 시 상세 정보"""
    error_code: str
    message: str
    details: Optional[str] = None
    log_ref_id: Optional[str] = None

class ComplianceAlert(BaseModel):
    """컴플라이언스 알림 상세 정보"""
    alert_code: str # 예: INSUFFICIENT_BREAK_TIME, EXCESSIVE_DAILY_OVERTIME
    message: str    # 사용자 친화적 알림 메시지
    severity: Literal["warning", "error", "info"] = "warning"
    details: Optional[Dict[str, Any]] = None # 추가 정보 (예: 관련 날짜, 초과 시간 등)

class WorkTimeCalculationResult(BaseModel):
    """근로시간 계산기의 최종 통합 출력 구조"""
    employee_id: Optional[str] = None
    period: str
    processing_mode: Literal["attendance", "timecard", "unknown", "error"]
    attendance_summary: Optional[AttendanceSummary] = None
    time_summary: Optional[TimeSummary] = None
    salary_basis: Optional[SalaryBasis] = None
    daily_calculation_details: Optional[List[WorkDayDetail]] = None
    warnings: List[str] = Field(default_factory=list)
    compliance_alerts: List[ComplianceAlert] = Field(default_factory=list)
    error: Optional[ErrorDetails] = None
    processed_timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    custom_fields: Optional[Dict[str, Any]] = None

# --- 입력 데이터 구조 --- #

class AttendanceInputRecord(BaseModel):
    """모드 A (AttendanceBasedCalculator) 입력 레코드"""
    date: datetime.date
    status_code: str
    worked_minutes: Optional[int] = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date_str(cls, value):
        if isinstance(value, str):
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
        return value

class AttendanceInputData(BaseModel):
    """모드 A 전체 입력 데이터"""
    employee_id: Optional[str] = None
    period: str # 예: "2025-05"
    records: List[AttendanceInputRecord]
    custom_fields: Optional[Dict[str, Any]] = None

class TimeCardRecord(BaseModel):
    """모드 B (TimeCardBasedCalculator) 입력 레코드"""
    date: datetime.date
    # day_type: Optional[Literal["weekday", "saturday", "sunday", "public_holiday"]] = None
    start_time: str # "HH:MM" - 필수 필드
    end_time: str   # "HH:MM" - 필수 필드
    break_time_minutes: Optional[int] = 0
    # is_holiday_work: Optional[bool] = None
    # leave_type: Optional[str] = None
    # leave_hours: Optional[Decimal] = None
    notes: Optional[str] = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date_str(cls, value):
        if isinstance(value, str):
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
        return value

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time_format(cls, value):
        if not value:
            raise ValueError("Time fields cannot be empty")
        if not re.match(r'^([01]\d|2[0-3]):([0-5]\d)$', value):
            raise ValueError(f"Time format should be HH:MM, got {value}")
        return value

class TimeCardInputData(BaseModel):
    """모드 B 전체 입력 데이터"""
    employee_id: Optional[str] = None
    period: str # 예: "2025-05"
    records: List[TimeCardRecord]
    hire_date: Optional[datetime.date] = None
    resignation_date: Optional[datetime.date] = None
    custom_fields: Optional[Dict[str, Any]] = None
    
    @field_validator("records")
    @classmethod
    def validate_records(cls, v):
        if not v:
            raise ValueError("Records cannot be empty")
        return v
    
    @field_validator("hire_date", "resignation_date", mode="before")
    @classmethod
    def parse_date_str(cls, value):
        if isinstance(value, str):
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
        return value

# --- 설정 관련 구조 --- #

class AttendanceStatusCodeDetails(BaseModel):
    """출근 상태 코드 의미 정의"""
    work_day_value: Decimal = Field(description="1.0 (정상), 0.5 (반차), 0.0 (결근) 등")
    is_paid_leave: bool = False
    is_unpaid_leave: bool = False
    counts_as_late: bool = False
    counts_as_early_leave: bool = False
    description: Optional[str] = None

class BreakTimeRule(BaseModel):
    threshold_minutes: int
    break_minutes: int

class RoundingPolicy(BaseModel):
    hours_rounding: Literal["none", "nearest_decimal_1", "nearest_decimal_2", "floor_minute_15", "ceil_minute_15"] = "none"
    # 추가적인 라운딩 정책 필드 가능

class CompanySettings(BaseModel):
    """settings.yaml 등에서 로드될 회사별 근로시간 관련 설정"""
    daily_work_minutes_standard: int = Field(default=480, description="일 소정근로시간(분)")
    weekly_work_minutes_standard: int = Field(default=2400, description="주 소정근로시간(분), 예: 40시간")
    night_shift_start_time: str = Field(default="22:00", pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    night_shift_end_time: str = Field(default="06:00", pattern=r"^([01]\d|2[0-3]):([0-5]\d)$")
    break_time_rules: List[BreakTimeRule] = Field(default_factory=list)
    attendance_status_codes: Dict[str, AttendanceStatusCodeDetails] = Field(default_factory=dict)
    rounding_policy: RoundingPolicy = Field(default_factory=RoundingPolicy)
    weekly_overtime_limit_buffer: int = Field(default=720, description="주간 연장근로 한도 초과 판단 시 버퍼(분), 예: 12시간")
    # ... 기타 필요한 설정

class MinimumWageYearly(BaseModel):
    hourly_rate: int
    monthly_equivalent: Optional[int] = None # 필요시 계산 또는 직접 입력

class MinimumWagesConfig(RootModel[Dict[str, MinimumWageYearly]]):
    root: Dict[str, MinimumWageYearly]

    def get_for_year(self, year: int) -> Optional[MinimumWageYearly]:
        return self.root.get(str(year))

class HolidayConfig(BaseModel):
    date: datetime.date
    name: str
    paid_status: Literal["paid", "unpaid"] = "paid"

    @field_validator("date", mode="before")
    @classmethod
    def parse_date_str(cls, value):
        if isinstance(value, str):
            return datetime.datetime.strptime(value, "%Y-%m-%d").date()
        return value

class HolidaysConfig(RootModel[List[HolidayConfig]]):
    root: List[HolidayConfig]

    def get_holidays_for_period(self, start_date: datetime.date, end_date: datetime.date) -> List[HolidayConfig]:
        return [h for h in self.root if start_date <= h.date <= end_date]

class GlobalWorkSettings(BaseModel):
    """최상위 설정 파일 구조 (예: settings.yaml 로드 결과)"""
    company_settings: CompanySettings = Field(default_factory=CompanySettings)
    minimum_wages_config: Optional[MinimumWagesConfig] = None
    holidays_config: Optional[HolidaysConfig] = None
