# Plan 020: 듀얼 모드 근로시간 계산기 - CLI 명령어 및 설정 정책 설계

## 1. 개요

이 문서는 `Plan 020: 듀얼 모드 근로시간 계산기`의 CLI 명령어 인터페이스, 설정 파일(`settings.yaml`) 연동 정책, 사용자 메시지 UX, 오류 처리 및 로깅 통합 방안을 상세히 기술합니다. 목표는 사용자가 근로시간 계산 모듈을 쉽고 효율적으로 사용할 수 있도록 직관적인 CLI를 제공하고, 다양한 운영 환경에 맞게 설정을 유연하게 관리할 수 있도록 하는 것입니다.

## 2. CLI 명령어 설계 (`calculate-hours`)

기존 `cli.py`에 `typer`를 사용하여 새로운 `calculate-hours` 명령어를 추가합니다.

### 2.1. 명령어 구조 및 옵션

```bash
python cli.py calculate-hours \
    --input-file <INPUT_CSV_OR_JSON_PATH> \
    --period <YYYY-MM> \
    [--mode <attendance|timecard|auto>] \
    [--employee-id <EMPLOYEE_ID>] \
    [--output-file <OUTPUT_JSON_PATH>] \
    [--settings-file <CUSTOM_SETTINGS_YAML_PATH>]
```

*   **`calculate-hours`**: 근로시간 계산을 수행하는 메인 명령어입니다.

*   **`--input-file` (필수)**:
    *   설명: 처리할 근태 데이터 파일 경로 (CSV 또는 JSON 형식).
    *   예시: `data/attendance_202505.csv`, `data/timecard_emp001_202505.json`
    *   유효성 검사: 파일 존재 여부, 지원되는 확장자(csv, json) 여부.

*   **`--period` (필수)**:
    *   설명: 처리 대상 연월 (YYYY-MM 형식).
    *   예시: `2025-05`
    *   유효성 검사: YYYY-MM 형식 일치 여부.

*   **`--mode` (선택, 기본값: `auto`)**:
    *   설명: 근로시간 계산 처리 모드 선택 (`attendance`, `timecard`, `auto`).
        *   `attendance`: 출근 상태 기반 계산 (모드 A).
        *   `timecard`: 출퇴근 시각 기반 계산 (모드 B - Plan 021 구현 예정).
        *   `auto`: 입력 데이터 특성을 분석하여 자동으로 모드 감지.
    *   예시: `--mode attendance`

*   **`--employee-id` (선택)**:
    *   설명: 특정 직원의 ID. 결과 JSON 파일에 포함되며, 로깅 시에도 활용될 수 있습니다.
    *   예시: `--employee-id EMP001`

*   **`--output-file` (선택)**:
    *   설명: 계산 결과를 저장할 JSON 파일 경로. 지정하지 않으면 표준 출력(stdout)으로 결과를 표시합니다.
    *   예시: `output/work_hours_emp001_202505.json`
    *   동작: 파일 경로가 주어지면, 해당 경로에 `WorkTimeCalculationResult` 스키마에 따른 JSON 데이터를 저장합니다. 디렉토리가 존재하지 않으면 생성합니다.

*   **`--settings-file` (선택)**:
    *   설명: 기본 `settings.yaml` 대신 사용할 사용자 정의 설정 파일 경로. 이를 통해 회사별 또는 특정 상황에 맞는 설정을 쉽게 적용할 수 있습니다.
    *   예시: `configs/company_a_settings.yaml`

### 2.2. 도움말 메시지 (Typer 자동 생성 활용)

Typer의 기능을 활용하여 각 명령어와 옵션에 대한 명확한 도움말 메시지를 제공합니다.

```python
# cli.py 내 예상 코드 일부
@app.command(help="근태 데이터를 기반으로 정규, 연장, 야간, 휴일 근로시간 등을 계산합니다.")
def calculate_hours(
    input_file: Path = typer.Option(..., "--input-file", "-i", help="처리할 근태 데이터 파일 경로 (CSV 또는 JSON)", exists=True, file_okay=True, dir_okay=False, readable=True),
    period: str = typer.Option(..., "--period", "-p", help="처리 대상 연월 (YYYY-MM 형식)", callback=validate_period_format),
    mode: Literal["attendance", "timecard", "auto"] = typer.Option("auto", "--mode", "-m", help="계산 처리 모드 (attendance, timecard, auto)"),
    employee_id: Optional[str] = typer.Option(None, "--employee-id", "-e", help="직원 ID (선택 사항)"),
    output_file: Optional[Path] = typer.Option(None, "--output-file", "-o", help="결과를 저장할 JSON 파일 경로 (미지정 시 표준 출력)"),
    settings_file: Optional[Path] = typer.Option(None, "--settings-file", "-s", help="사용자 정의 설정 파일 경로 (기본 settings.yaml 대체)", exists=True, file_okay=True, readable=True)
):
    # ... 로직 ...
    pass
```

## 3. 설정 정책 (`settings.yaml` 연동)

### 3.1. `settings.yaml` 내 근로시간 관련 설정 구조

기존 `settings.yaml` 파일에 근로시간 계산 모듈(`WorkTimeSettings` 스키마)을 위한 설정을 추가합니다. `work_time_schema.py`에 정의된 `WorkTimeSettings` TypedDict 구조를 따릅니다.

```yaml
# settings.yaml 예시
# ... (기존 설정들) ...

work_time_config: # 최상위 키로 그룹화
  default_company_id: "DEFAULT_COMP"
  companies:
    DEFAULT_COMP: # 기본 회사 설정
      company_id: "DEFAULT_COMP"
      default_daily_scheduled_hours: 8.0
      default_weekly_scheduled_hours: 40.0
      overtime_rules: 
        default_rate: 1.5
        # ... 기타 연장근로 규칙 ...
      night_work_rules:
        start_time: "22:00"
        end_time: "06:00"
        rate: 0.5 # 통상임금의 50% 가산
      holiday_rules:
        default_work_rate: 1.5 # 휴일근로 기본 가산율 (8시간 이내)
        over_8h_rate: 2.0    # 휴일근로 8시간 초과 시 가산율
        public_holidays: # 연도-월별 공휴일 목록 (YYYY-MM: ["YYYY-MM-DD", ...])
          "2025-01": ["2025-01-01"]
          "2025-05": ["2025-05-01", "2025-05-05", "2025-05-15"]
          # ... 기타 월별 공휴일 ...
      break_time_rules: # 근무시간에 따른 자동 휴게시간 부여 규칙
        - work_hours_threshold: 4.0 # 4시간 이상 근무 시
          break_minutes: 30
        - work_hours_threshold: 8.0 # 8시간 이상 근무 시
          break_minutes: 60 # 누적 (즉, 4시간 30분 + 추가 30분)
      attendance_status_codes: # 모드 A (AttendanceBasedCalculator)용 상태 코드 정의
        "1": { "work_day_value": 1.0, "is_paid_leave": false, "is_unpaid_leave": false, "counts_as_late": false, "counts_as_early_leave": false, "description": "정상근무" }
        "0.5A": { "work_day_value": 0.5, "is_paid_leave": true, "is_unpaid_leave": false, "counts_as_late": false, "counts_as_early_leave": false, "description": "오전 유급반차" }
        "0": { "work_day_value": 0.0, "is_paid_leave": false, "is_unpaid_leave": true, "counts_as_late": false, "counts_as_early_leave": false, "description": "무급결근" }
        "L": { "work_day_value": 1.0, "is_paid_leave": false, "is_unpaid_leave": false, "counts_as_late": true, "counts_as_early_leave": false, "description": "지각 (정상근무로 처리)" }
        "SICK_P": { "work_day_value": 1.0, "is_paid_leave": true, "is_unpaid_leave": false, "counts_as_late": false, "counts_as_early_leave": false, "description": "유급병가" }
        # ... 기타 상태 코드 정의 ...
    COMPANY_B: # 다른 회사 설정 (필요시)
      company_id: "COMPANY_B"
      # ... COMPANY_B 만의 특정 설정 ...
      attendance_status_codes: # COMPANY_B는 다른 상태 코드를 사용할 수 있음
        "P": { "work_day_value": 1.0, "description": "Present" }
        # ...

# ... (기타 설정들) ...
```

### 3.2. 설정 로딩 메커니즘

*   `cli.py` 또는 별도의 설정 로더 모듈에서 `settings.yaml` (또는 `--settings-file`로 지정된 파일)을 로드합니다.
*   `WorkTimeProcessor` 초기화 시, 해당 `company_id` (명시적 지정 또는 기본값)에 맞는 설정을 추출하여 `WorkTimeSettings` 객체로 전달합니다.
*   `company_id`는 추후 다중 회사 지원 시 중요한 역할을 합니다. 현재는 기본 회사 설정을 사용하거나, CLI 옵션으로 받을 수 있습니다.

## 4. 사용자 메시지 UX 및 오류 처리

### 4.1. 성공 메시지

*   결과를 파일로 저장 시: `[SUCCESS] 근로시간 계산 완료. 결과가 {output_file} 파일에 저장되었습니다.`
*   결과를 표준 출력 시: `[INFO] 근로시간 계산 결과:` 다음 줄에 JSON 출력.

### 4.2. 오류 메시지 (CLI 레벨)

*   파일 관련: `[ERROR] 입력 파일 {input_file}을(를) 찾을 수 없습니다. 경로를 확인해주세요.`
*   옵션 관련: `[ERROR] 기간({period}) 형식이 잘못되었습니다. YYYY-MM 형식으로 입력해주세요.`
*   Typer의 기본 유효성 검사 메시지를 최대한 활용하고, 필요시 커스텀 콜백으로 보강합니다.

### 4.3. 경고 및 정보 메시지 (모듈 레벨, CLI 통해 전달)

*   `WorkTimeCalculationResult`의 `warnings` 리스트에 포함된 내용을 CLI에서 적절히 표시합니다.
    *   예: `[WARNING] 입력 데이터 처리 중 다음 경고가 발생했습니다:
        - Date 2025-05-08: Unknown status_code 'UNKNOWN'. Will be ignored.
        - ...`
*   `WorkTimeCalculationResult`의 `error` 필드가 채워진 경우, 해당 오류 정보를 사용자 친화적으로 표시합니다.
    *   예: `[ERROR] 근로시간 계산 중 오류 발생: {error.message} (오류 코드: {error.error_code}, 로그 참조 ID: {error.log_reference_id})`

### 4.4. 로깅 통합

*   기존 `cli.py`의 로깅 설정을 따릅니다 (`operation_logger`).
*   `calculate-hours` 명령어 실행 시작/종료, 주요 파라미터, 발생한 오류/경고 등을 로그에 기록합니다.
*   `WorkTimeProcessor` 및 하위 계산기 모듈에서 발생하는 로그(INFO, WARNING, ERROR 레벨)도 통합 로깅 시스템에 의해 처리됩니다.
*   민감 정보(예: 개인 식별 정보가 포함된 상세 근태 데이터)는 기본적으로 DEBUG 레벨에서만 로깅하거나, 마스킹 처리 후 로깅하는 것을 고려합니다 (Log Sanitizer 연동).

## 5. `cli.py` 통합 방안

1.  **설정 로드**: `settings.yaml`에서 `work_time_config` 섹션을 로드하는 함수를 구현하거나 기존 로더를 확장합니다.
2.  **Typer 명령어 추가**: 위 2.2.에 기술된 대로 `calculate_hours` 함수를 `cli.py`의 `app`에 추가합니다.
3.  **`WorkTimeProcessor` 인스턴스화**: 로드된 설정과 함께 `WorkTimeProcessor`를 초기화합니다.
4.  **입력 데이터 처리**: `--input-file`로 지정된 CSV 또는 JSON 파일을 읽어 `WorkTimeProcessor`가 처리할 수 있는 형식(예: `List[Dict]`)으로 변환합니다. (CSV 파싱 로직 필요)
5.  **`processor.process()` 호출**: 준비된 입력 데이터, 기간, 모드 등의 인자와 함께 `processor.process()`를 호출합니다.
6.  **결과 처리**: 반환된 `WorkTimeCalculationResult`를 분석합니다.
    *   `error` 필드가 있으면 오류 메시지를 출력하고 로깅합니다.
    *   `warnings` 필드가 있으면 경고 메시지를 출력하고 로깅합니다.
    *   정상 처리된 경우, `--output-file` 지정 여부에 따라 결과를 파일에 저장하거나 표준 출력합니다.

## 6. 향후 고려 사항

*   대용량 데이터 처리 시 진행률 표시 기능.
*   다양한 CSV/JSON 입력 형식 변형에 대한 유연한 대응.
*   `TimeCardBasedCalculator` (모드 B) 구현 및 통합 (Plan 021).

이 설계를 바탕으로 `cli.py` 수정 및 관련 유틸리티 함수 구현을 진행합니다.
