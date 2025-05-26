# Plan 020: 듀얼 모드 근로시간 계산기 - 스키마 및 설계

## 1. 개요

본 문서는 "듀얼 모드 근로시간 계산기"의 핵심 데이터 구조, 클래스 인터페이스, 공통 출력 포맷, 오류 처리 방안, 로깅 정책, CLI 출력 기준 등을 정의합니다. 이 설계는 `/home/ubuntu/upload/payslip/work_time_schema.py` 파일 및 관련 모듈 구현의 기반이 됩니다.

## 2. 예상 디렉토리 구조 (재확인)

```
payslip/
├── work_time_processor.py         # 통합 컨트롤러
├── attendance_calculator.py       # 모드 A: 출근 상태 기반
├── timecard_calculator.py         # 모드 B: 출퇴근 시각 기반 (Plan 021에서 상세 구현)
├── work_time_schema.py            # 본 문서에서 정의하는 데이터 구조 및 공통 포맷
└── utils/                         # (선택적) 공통 유틸리티 함수 (예: 시간 파싱, 날짜 계산 등)
      └── time_utils.py
tests/
├── test_work_time_processor.py
├── test_attendance_calculator.py
└── test_timecard_calculator.py
```

## 3. 핵심 클래스 인터페이스 및 역할

### 3.1. `WorkTimeProcessor` (`work_time_processor.py`)

*   **역할**: 입력 데이터와 모드(명시적 또는 자동 감지)에 따라 적절한 계산기(`AttendanceBasedCalculator` 또는 `TimeCardBasedCalculator`)를 선택하고, 계산을 실행한 후 공통 포맷으로 결과를 반환하는 통합 컨트롤러입니다.
*   **주요 메서드**:
    *   `__init__(self, settings: dict)`: 회사별 설정값(주휴수당 기준, 공제율 등)을 로드합니다.
    *   `process(self, input_data: dict | list, mode: str = 'auto', employee_id: str = None, period: str = None) -> dict`: 
        *   `input_data`: 원시 근태 데이터 (CSV 파싱 결과 또는 직접 입력된 딕셔너리/리스트).
        *   `mode`: "attendance", "timecard", 또는 "auto". "auto"일 경우 입력 데이터 특성을 분석하여 모드 자동 감지 시도.
        *   `employee_id`, `period`: 결과에 포함될 직원 ID 및 기간 정보.
        *   반환값: 아래 "5. 공통 출력 포맷"에 정의된 딕셔너리.

### 3.2. `AttendanceBasedCalculator` (`attendance_calculator.py`)

*   **역할**: 출근/결근/지각 등 일별 상태가 표기된 데이터를 기반으로 출근율, 근무일수, 공제일수, 실급여일수 등을 계산합니다.
*   **입력 데이터 형식 (예시)**: 일별 상태 코드를 포함하는 리스트. 각 항목은 날짜와 상태 코드(예: `1`=정상출근, `0.5`=반차, `0`=결근, `H`=휴일, `L`=지각, `E`=조퇴 등)를 가집니다. 상세 코드는 `settings.yaml` 또는 내부 정책으로 정의됩니다.
    ```json
    // 예시 input_data for AttendanceBasedCalculator
    [
        {"date": "2025-05-01", "status_code": "1"},
        {"date": "2025-05-02", "status_code": "L"}, // 지각
        {"date": "2025-05-03", "status_code": "0.5A"}, // 오전 반차
        {"date": "2025-05-06", "status_code": "0"} // 결근
    ]
    ```
*   **주요 메서드**:
    *   `__init__(self, settings: dict)`: 관련 설정값(상태 코드 정의, 만근 기준일 등) 로드.
    *   `calculate(self, attendance_data: list[dict], period_info: dict) -> dict`: 
        *   `attendance_data`: 위에서 정의된 입력 데이터.
        *   `period_info`: 해당 월의 총 일수, 주말/공휴일 정보 등.
        *   반환값: "5. 공통 출력 포맷" 중 `work_summary` 및 `salary_basis` 관련 항목을 채운 딕셔너리.

### 3.3. `TimeCardBasedCalculator` (`timecard_calculator.py`)

*   **역할**: 출퇴근 시각, 휴게시간 등의 시간 기록을 기반으로 정규, 연장, 야간, 휴일 시간 등을 누계 계산합니다. (상세 구현은 Plan 021)
*   **입력 데이터 형식**: `/home/ubuntu/upload/work_time_data_structure.md`에 정의된 `timecard_data` 구조를 따르거나 확장합니다.
*   **주요 메서드**:
    *   `__init__(self, settings: dict)`: 관련 설정값(연장/야간 기준 시간, 가산율 정책 등) 로드.
    *   `calculate(self, timecard_data: list[dict], period_info: dict) -> dict`:
        *   반환값: "5. 공통 출력 포맷" 중 `time_summary` 관련 항목을 채운 딕셔너리.

## 4. `work_time_schema.py` 주요 내용 (데이터 구조 정의)

이 파일은 Pydantic 모델 또는 TypedDict 등을 사용하여 공통 입출력 데이터 구조를 정의합니다.

```python
# /home/ubuntu/upload/payslip/work_time_schema.py (예시)
from typing import TypedDict, List, Optional, Dict, Any, Literal
from decimal import Decimal

class WorkSummary(TypedDict):
    total_days_in_period: int          # 해당 기간의 총 역일 수
    scheduled_work_days: int         # 소정근로일수 (주말/공휴일 제외)
    actual_work_days: Decimal          # 실제 출근일수 (예: 1, 0.5)
    paid_leave_days: Decimal           # 유급휴가일수 (연차, 병가 등)
    unpaid_leave_days: Decimal         # 무급휴가/결근일수
    late_count: int                    # 지각 횟수
    early_leave_count: int             # 조퇴 횟수
    # attendance_rate: Optional[Decimal] # 출근율 (필요시)

class TimeSummary(TypedDict):
    regular_hours: Decimal             # 정규 근로시간
    overtime_hours: Decimal            # 총 연장 근로시간
    night_hours: Decimal               # 총 야간 근로시간 (정규/연장과 중복 가능)
    holiday_work_hours: Decimal        # 총 휴일 근로시간 (정규/연장과 중복 가능)
    # 상세 가산율별 시간은 필요시 하위 딕셔너리로 추가 (예: overtime_details: {'1.5x': 10, '2.0x': 2})

class SalaryBasis(TypedDict):
    # 모드 A (AttendanceBased) 결과가 주로 반영
    base_salary_for_period: Decimal  # 해당 기간의 기준 급여 (월급제인 경우)
    actual_payment_days: Decimal       # 실 급여 지급 대상일수 (만근일수 - 무급공제일수 등)
    deduction_days: Decimal            # 무급 결근/휴가 등으로 인한 공제일수
    work_ratio: Optional[Decimal]      # (실 근무일 / 소정근로일) 등 급여 계산 비율 (필요시)

class ErrorDetail(TypedDict):
    error_code: str                    # 예: INPUT_FORMAT_ERROR, CALCULATION_FAILED
    message: str                       # 사용자 친화적 오류 메시지
    details: Optional[str]             # 개발자용 상세 정보
    log_reference_id: Optional[str]    # 로그 추적용 ID

class WorkTimeCalculationResult(TypedDict):
    employee_id: Optional[str]
    period: str                        # 예: "2025-05"
    processing_mode: Literal['attendance', 'timecard', 'unknown'] # 실제 처리된 모드
    work_summary: Optional[WorkSummary]  # AttendanceBasedCalculator 결과 중심
    time_summary: Optional[TimeSummary]  # TimeCardBasedCalculator 결과 중심
    salary_basis: Optional[SalaryBasis]  # 주로 AttendanceBasedCalculator 결과와 연동
    warnings: List[str]                # 처리 중 발생한 경고 메시지 리스트
    error: Optional[ErrorDetail]       # 오류 발생 시 채워짐, 정상 처리 시 None
    raw_input_summary: Optional[Dict[str, Any]] # (선택적) 입력 데이터 요약 정보
    processed_timestamp: str           # 처리 완료 시각 (ISO 형식)
```

## 5. 공통 출력 포맷 (JSON)

`WorkTimeProcessor`는 최종적으로 `WorkTimeCalculationResult` TypedDict (또는 Pydantic 모델)에 정의된 구조를 따르는 Python 딕셔너리를 반환하며, 이는 JSON으로 쉽게 직렬화될 수 있습니다. 사용자 제공 예시를 기반으로 하되, 모드별 특성을 반영하고 오류 정보를 포함할 수 있도록 확장합니다.

**정상 처리 시 예시 (일부 필드만 표시):**
```json
{
  "employee_id": "EMP001",
  "period": "2025-05",
  "processing_mode": "attendance", // 또는 "timecard"
  "work_summary": {
    "total_days_in_period": 31,
    "scheduled_work_days": 22,
    "actual_work_days": 20.5,
    "paid_leave_days": 1.5,
    "unpaid_leave_days": 0,
    "late_count": 1,
    "early_leave_count": 0
  },
  "time_summary": null, // attendance 모드에서는 비활성화 또는 기본값
  "salary_basis": {
    "base_salary_for_period": 3000000,
    "actual_payment_days": 22, // (소정근로일 - 무급공제일) 또는 다른 기준
    "deduction_days": 0,
    "work_ratio": 0.9318 // (20.5 / 22)
  },
  "warnings": ["2025-05-15: 상태 코드 'X'는 정의되지 않은 코드입니다. 무시하고 처리합니다."],
  "error": null,
  "processed_timestamp": "2025-05-15T14:45:00Z"
}
```

**오류 발생 시 예시:**
```json
{
  "employee_id": "EMP002",
  "period": "2025-06",
  "processing_mode": "unknown", // 모드 감지 실패 또는 처리 전 오류
  "work_summary": null,
  "time_summary": null,
  "salary_basis": null,
  "warnings": [],
  "error": {
    "error_code": "INPUT_FILE_NOT_FOUND",
    "message": "입력 파일 'input_data.csv'을(를) 찾을 수 없습니다. 파일 경로를 확인해주세요.",
    "details": "FileNotFoundError: [Errno 2] No such file or directory: 'input_data.csv'",
    "log_reference_id": "LOG_WORK_TIME_ERR_12345"
  },
  "processed_timestamp": "2025-05-15T14:50:00Z"
}
```

## 6. 오류 처리, 사용자 메시지 UX, 로깅 정책

### 6.1. 오류 유형 및 코드 (예시 `error_code`)
*   `INPUT_FILE_NOT_FOUND`: 입력 파일을 찾을 수 없음.
*   `INPUT_FILE_READ_ERROR`: 입력 파일 읽기 오류 (권한 등).
*   `INPUT_FORMAT_INVALID`: 입력 데이터 형식이 유효하지 않음 (CSV 파싱 실패, JSON 구조 오류 등).
*   `MISSING_REQUIRED_FIELD`: 필수 입력 필드 누락 (예: 날짜, 상태 코드, 출퇴근 시각 등).
*   `INVALID_DATA_VALUE`: 필드 값 유효성 오류 (예: 잘못된 날짜 형식, 비정상적 시간 값).
*   `MODE_DETECTION_FAILED`: 자동 모드 감지 실패.
*   `CALCULATION_LOGIC_ERROR`: 내부 계산 로직 오류 (예상치 못한 예외).
*   `SETTINGS_NOT_FOUND`: 필수 설정값(`settings.yaml`) 누락.
*   `UNKNOWN_ERROR`: 기타 알 수 없는 오류.

### 6.2. 사용자 메시지 UX 가이드라인
*   **명확성**: 사용자가 문제를 이해하고 조치할 수 있도록 쉽고 명확한 언어 사용.
*   **구체성**: 오류 발생 시 어떤 부분에서 문제가 발생했는지(예: 파일명, 특정 데이터 행) 가능한 구체적으로 명시.
*   **조치 안내**: 사용자가 시도해볼 수 있는 해결 방법 제시 (예: "파일 경로를 확인하세요", "입력 데이터 형식을 점검하세요", "관리자에게 문의하세요(로그 ID: XXXXX)").
*   **일관성**: 유사한 오류에 대해 일관된 메시지 톤과 형식 유지.
*   **CLI 출력**: 성공 시 요약 정보, 오류 시 표준 오류 메시지 및 로그 참조 안내. `--verbose` 옵션 시 상세 정보 출력.

### 6.3. 로깅 구조 및 정책
*   **라이브러리**: Python 표준 `logging` 모듈 사용.
*   **로그 레벨**:
    *   `DEBUG`: 상세 개발 정보, 변수 값, 함수 호출 순서 등.
    *   `INFO`: 주요 처리 단계, 모드 감지 결과, 성공/실패 요약, 설정 로드 정보 등.
    -   `WARNING`: 예상치 못한 상황이지만 처리는 계속되는 경우 (예: 알 수 없는 상태 코드 무시, 기본값 사용 등). `WorkTimeCalculationResult`의 `warnings` 필드와 연동.
    *   `ERROR`: 처리 중단이 필요한 오류 발생. `WorkTimeCalculationResult`의 `error` 필드와 연동.
    *   `CRITICAL`: 시스템 수준의 심각한 오류 (거의 사용 안 함).
*   **로그 포맷**: `%(asctime)s - %(name)s - %(levelname)s - %(module)s.%(funcName)s:%(lineno)d - %(message)s`
*   **로그 파일**: `output/logs/work_time_YYYY-MM-DD.log` (날짜별 분리). 필요시 `employee_id`별 또는 `run_id`별 세분화 고려.
*   **로깅 항목**: 모듈 실행 시작/종료, 입력 데이터 요약, 선택된 모드, 주요 계산 단계 결과, 발생한 모든 예외 정보(traceback 포함), 최종 결과(성공/실패) 등.
*   `log_reference_id`: 심각한 오류 발생 시 고유 ID를 생성하여 로그에 기록하고, 사용자에게 해당 ID를 안내하여 추적 용이성 확보.

## 7. CLI 명령어 및 설정 정책 (초안)

### 7.1. CLI 명령어 (cli.py에 추가될 내용)
*   `python cli.py process-work-time --file <filepath> --period <YYYY-MM> [--mode <attendance|timecard|auto>] [--output-file <output.json>] [--employee-id <id>]`
    *   `--file`: 입력 근태 데이터 파일 경로 (CSV, JSON 등).
    *   `--period`: 처리 대상 연월.
    *   `--mode`: (선택) 명시적 모드 지정. 기본값 `auto`.
    *   `--output-file`: (선택) 결과 JSON 저장 경로. 미지정 시 stdout 출력.
    *   `--employee-id`: (선택) 단일 직원 처리 시 ID 지정.

### 7.2. 설정 정책 (`settings.yaml` 또는 별도 config)
*   `work_time_settings` 섹션 추가:
    *   `attendance_mode_codes`: 출근 상태 기반 모드에서 사용될 상태 코드와 의미 정의 (예: `1: full_day_work`, `0.5A: half_day_am_leave`).
    *   `timecard_mode_rules`: 연장/야간/휴일 기준 시간, 가산율, 최소 휴게시간 정책 등.
    *   `default_scheduled_hours`: 일/주 소정근로시간 기본값.
    *   `holiday_definitions`: 회사 지정 휴일 목록 또는 API 연동 정보.
    *   `log_level`: 기본 로깅 레벨 (DEBUG, INFO 등).

이 문서는 초기 설계이며, 실제 구현 과정에서 피드백과 테스트를 통해 지속적으로 개선될 수 있습니다.

