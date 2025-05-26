# 근로시간 계산 모듈 데이터 구조 설계 (플랜 020)

## 1. 입력 데이터 (`timecard_data`) 구조 정의

`timecard_data`는 직원별로 특정 기간 동안의 일별 근태 기록 리스트로 구성됩니다. 각 일별 기록은 다음 정보를 포함하는 딕셔너리 형태를 가정합니다.

**기본 가정:**
*   입력 데이터는 JSON 파일 또는 Python 리스트/딕셔너리 형태로 제공될 수 있습니다.
*   시간은 "HH:MM" (24시간제) 형식의 문자열로 표현됩니다.
*   날짜는 "YYYY-MM-DD" 형식의 문자열로 표현됩니다.

**일별 근태 기록 (`daily_record`) 상세 필드:**

```json
{
  "employee_id": "EMP001", // (선택적, 데이터가 직원별 파일로 분리되지 않은 경우)
  "date": "2025-07-01", // 근무일 (필수)
  "day_type": "weekday", // 요일 유형 (예: "weekday", "saturday", "sunday", "public_holiday") (필수)
  "shift_start_time": "09:00", // 소정근로 시작 시간 (필수, 회사의 기본 근무 시작 시간)
  "shift_end_time": "18:00", // 소정근로 종료 시간 (필수, 회사의 기본 근무 종료 시간)
  "actual_clock_in": "08:55", // 실제 출근 시간 (필수)
  "actual_clock_out": "19:30", // 실제 퇴근 시간 (필수)
  "break_time_minutes": 60, // 총 휴게 시간(분 단위) (필수, 법정 휴게시간 또는 실제 부여된 휴게시간)
  "is_holiday_work": false, // 휴일 근무 여부 (true/false, day_type이 "public_holiday"이고 실제 근무 시 true)
  "leave_type": null, // 휴가 유형 (예: "annual", "sick_paid", "sick_unpaid", "maternity", "paternity", null 등)
  "leave_hours": 0, // 휴가 시간 (시간 단위, 예: 반차 시 4시간)
  "work_location_code": "OFFICE_MAIN", // (선택적) 근무지 코드 (예: 재택, 외근 등 구분)
  "notes": "프로젝트 마감으로 인한 연장근무" // (선택적) 특이사항 기록
}
```

**필드 설명:**
*   `employee_id`: 직원 ID. 데이터가 직원별로 집계되어 있다면 최상위 레벨에 한 번만 있을 수도 있습니다.
*   `date`: 근무일자.
*   `day_type`: 해당 날짜의 유형. 주중, 토요일, 일요일, 공휴일 등을 구분하여 휴일근무 및 가산 수당 계산에 활용됩니다.
*   `shift_start_time`, `shift_end_time`: 해당 직원의 소정근로시간(계약된 근무시간)의 시작과 끝을 나타냅니다. 유연근무제 등을 고려하여 일별로 다를 수 있습니다.
*   `actual_clock_in`, `actual_clock_out`: 실제 출퇴근 기록입니다.
*   `break_time_minutes`: 해당 근무일에 부여된 총 휴게시간(분)입니다. 근로기준법에 따라 4시간 근무 시 30분, 8시간 근무 시 1시간 이상 부여되어야 합니다.
*   `is_holiday_work`: 해당일이 공휴일 또는 약정휴일이고 실제 근로를 제공했는지 여부입니다. `day_type`과 함께 판단하여 휴일근로시간을 산정합니다.
*   `leave_type`: 사용한 휴가 유형입니다. 연차, 병가(유급/무급), 출산휴가, 육아휴직 등을 구분합니다. 휴가 유형에 따라 근로시간 산정 방식이 달라질 수 있습니다 (예: 유급휴가는 소정근로시간으로 인정).
*   `leave_hours`: 휴가를 사용한 시간입니다. 전일 휴가, 반차, 시간 단위 휴가 등을 반영합니다.
*   `work_location_code`: (선택 사항) 근무지 코드. 재택근무, 출장 등 특수 상황을 기록할 수 있습니다.
*   `notes`: (선택 사항) 해당일의 근태 관련 특이사항을 기록합니다.

**예시 `timecard_data` (직원 1명의 2일치 기록):**

```json
[
  {
    "date": "2025-07-01",
    "day_type": "weekday",
    "shift_start_time": "09:00",
    "shift_end_time": "18:00",
    "actual_clock_in": "08:55",
    "actual_clock_out": "20:30",
    "break_time_minutes": 60,
    "is_holiday_work": false,
    "leave_type": null,
    "leave_hours": 0,
    "notes": "야근"
  },
  {
    "date": "2025-07-02",
    "day_type": "weekday",
    "shift_start_time": "09:00",
    "shift_end_time": "18:00",
    "actual_clock_in": "09:00",
    "actual_clock_out": "13:00",
    "break_time_minutes": 0, // 4시간 미만 근무로 휴게시간 없음
    "is_holiday_work": false,
    "leave_type": "annual_half_day_pm", // 오후 반차
    "leave_hours": 4,
    "notes": "오후 반차 사용"
  },
  {
    "date": "2025-07-06",
    "day_type": "sunday", // 일요일
    "shift_start_time": "09:00", // 휴일이지만 소정근로시간은 참고용으로 있을 수 있음
    "shift_end_time": "18:00",
    "actual_clock_in": "10:00",
    "actual_clock_out": "15:00",
    "break_time_minutes": 30,
    "is_holiday_work": true, // 휴일 근무
    "leave_type": null,
    "leave_hours": 0,
    "notes": "긴급 장애 처리 지원"
  }
]
```

## 2. 출력 데이터 (`calculated_work_hours`) 구조 정의

`calculate_work_hours` 함수는 특정 기간(예: 월별) 동안의 총 집계된 근로시간 정보를 반환합니다. 이 정보는 향후 급여 계산에 직접 활용될 수 있도록 설계합니다.

**출력 딕셔너리 상세 필드:**

```json
{
  "employee_id": "EMP001", // (선택적, 입력에 따라)
  "period_start_date": "2025-07-01", // 집계 기간 시작일
  "period_end_date": "2025-07-31", // 집계 기간 종료일
  "total_work_days": 22, // 총 실근무일수 (유급휴가일 포함 가능, 정책에 따라)
  "total_paid_leave_days": 1.5, // 총 유급휴가 사용일수 (예: 연차, 병가 등)
  "summary_hours": {
    "total_scheduled_hours": 176.0, // 총 소정근로시간 (해당 기간의 근무일 기준)
    "total_actual_work_hours": 182.5, // 총 실근로시간 (휴게시간 제외, 연장/야간/휴일 포함)
    "total_recognized_work_hours": 180.0, // 총 인정근로시간 (유급휴가 시간 등을 소정근로로 인정한 시간 포함)
    "total_break_time_hours": 22.0 // 총 휴게시간
  },
  "detailed_hours": {
    "regular_hours": 160.0, // 총 정규 근로시간 (소정근로시간 내 실근로)
    "overtime_hours": {
      "weekdays_1_5x": 10.0, // 평일 연장근로 (기본 8시간 초과, 1.5배 가산 대상)
      "weekdays_2_0x": 2.0,  // (선택적) 평일 특정시간 이후 연장 (예: 22시 이후 연장 시 0.5배 추가 가산)
      "holidays_1_5x": 5.0,  // 휴일 연장근로 (8시간 이내, 1.5배 가산 대상)
      "holidays_2_0x": 1.0   // 휴일 연장근로 (8시간 초과, 2.0배 가산 대상)
    },
    "night_hours": 8.0, // 총 야간 근로시간 (22:00 ~ 익일 06:00 사이 근로, 0.5배 가산 대상)
                               // 이 시간은 regular_hours 또는 overtime_hours와 중복될 수 있음 (가산 수당 계산용)
    "holiday_hours": {
        "paid_holiday_work_hours_within_8": 4.0, // 유급휴일 8시간 이내 근로 (1.5배 대상)
        "paid_holiday_work_hours_over_8": 1.0,   // 유급휴일 8시간 초과 근로 (2.0배 대상)
        "unpaid_holiday_work_hours": 0.0       // 무급휴일 근로 (1.0배 또는 회사 정책에 따름)
    }
  },
  "exceptions_summary": [
    {"type": "lateness", "count": 1, "total_minutes": 15},
    {"type": "early_leave", "count": 0, "total_minutes": 0},
    {"type": "absenteeism_unpaid", "count": 0}
  ],
  "warnings": [
    "2025-07-15: 기록된 휴게시간이 법정 최소 휴게시간보다 적습니다."
  ] // 처리 중 발생한 경고 메시지 리스트
}
```

**필드 설명:**
*   `employee_id`, `period_start_date`, `period_end_date`: 대상 직원 및 집계 기간 정보.
*   `total_work_days`: 실제 근로를 제공한 날의 수. 유급휴가를 근무일로 산정할지 여부는 정책에 따라 달라질 수 있습니다.
*   `total_paid_leave_days`: 사용한 유급휴가 총 일수 (시간을 일로 환산).
*   `summary_hours`:
    *   `total_scheduled_hours`: 해당 기간 동안의 총 소정근로시간.
    *   `total_actual_work_hours`: 실제 근로한 총 시간 (휴게시간 제외).
    *   `total_recognized_work_hours`: 급여계산을 위해 인정되는 총 근로시간 (유급휴가 등을 근로시간으로 간주).
    *   `total_break_time_hours`: 총 휴게시간.
*   `detailed_hours`:
    *   `regular_hours`: 소정근로시간 내에서 이루어진 실제 근로시간.
    *   `overtime_hours`: 연장근로시간을 가산율에 따라 세분화. (주 40시간, 일 8시간 초과분)
        *   `weekdays_1_5x`: 평일 1.5배 가산 대상 연장근로.
        *   `weekdays_2_0x`: (필요시) 평일 특정 조건 하 2.0배 가산 대상 연장근로.
        *   `holidays_1_5x`: 휴일 8시간 이내 근로 (1.5배).
        *   `holidays_2_0x`: 휴일 8시간 초과 근로 (2.0배).
    *   `night_hours`: 야간근로시간 (22시~06시). 이 시간은 정규 또는 연장근로와 중복될 수 있으며, 별도로 0.5배 가산됩니다.
    *   `holiday_hours`: 휴일근로시간을 유급/무급 및 시간에 따라 세분화.
*   `exceptions_summary`: 지각, 조퇴, 결근 등 주요 근태 예외사항 요약.
*   `warnings`: 데이터 처리 중 발생한 경고 메시지 (예: 법정 휴게시간 미준수 의심, 출퇴근 기록 누락 등).

이 데이터 구조는 근로기준법의 주요 사항(연장/야간/휴일 가산)을 반영하고, 다양한 예외 상황을 기록하여 정확한 급여 계산 및 근태 관리를 지원하는 것을 목표로 합니다. 세부 항목은 회사의 정책 및 관리 수준에 따라 추가되거나 수정될 수 있습니다.

