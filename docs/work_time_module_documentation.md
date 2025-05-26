# Plan 020: 듀얼 모드 근로시간 계산기 - 모듈 종합 문서

## 1. 개요

이 문서는 `Plan 020: 듀얼 모드 근로시간 계산기` 프로젝트의 전체 아키텍처, 핵심 모듈, 데이터 흐름, CLI 사용법, 설정 방법, 오류 처리 전략 및 코드 구조를 종합적으로 설명합니다. 본 문서는 개발자와 사용자가 모듈을 이해하고 효과적으로 활용하는 데 필요한 모든 정보를 제공하는 것을 목표로 합니다.

**주요 기능:**

*   **듀얼 모드 지원**: 출근 상태 기반(Attendance-based) 및 출퇴근 시각 기반(Timecard-based)의 두 가지 근태 데이터 입력 방식을 지원합니다.
*   **자동 모드 감지**: 입력 데이터의 특성을 분석하여 적절한 계산 모드를 자동으로 선택할 수 있습니다.
*   **유연한 설정**: `settings.yaml` 파일을 통해 회사별 정책(소정근로시간, 공휴일, 상태 코드 정의 등)을 유연하게 설정할 수 있습니다.
*   **통합된 출력**: 다양한 입력에도 불구하고 일관된 JSON 형식으로 계산 결과를 제공합니다.
*   **CLI 인터페이스**: 사용하기 쉬운 CLI 명령어를 통해 모듈 기능을 실행하고 결과를 관리할 수 있습니다.

## 2. 시스템 아키텍처

본 근로시간 계산 모듈은 다음과 같은 주요 구성 요소로 이루어져 있습니다.

*   **`WorkTimeProcessor` (통합 컨트롤러)**: 입력 데이터와 설정을 받아 적절한 계산기(Attendance-based 또는 Timecard-based)를 선택하고, 계산을 실행한 후 결과를 공통 포맷으로 반환하는 핵심 클래스입니다.
*   **`AttendanceBasedCalculator` (모드 A 계산기)**: 출근/결근/지각 등 일별 상태가 표기된 데이터를 기반으로 출근율, 근무일수, 공제일수 등을 계산합니다.
*   **`TimeCardBasedCalculator` (모드 B 계산기)**: 출퇴근 시각 및 휴게시간 기록을 기반으로 정규, 연장, 야간, 휴일 근로시간을 상세하게 계산합니다. (본 Plan 020에서는 스캐폴드만 구성, Plan 021에서 상세 구현 예정)
*   **`work_time_schema.py` (데이터 스키마)**: 모듈에서 사용되는 모든 입출력 데이터 구조(TypedDict 활용), 오류 형식, 설정 객체 타입을 정의하여 데이터의 일관성과 유효성을 보장합니다.
*   **`cli.py` (명령줄 인터페이스)**: `typer` 라이브러리를 사용하여 `calculate-hours` 명령어를 제공하며, 사용자가 파일 입력, 기간 설정, 모드 선택 등을 쉽게 할 수 있도록 지원합니다.
*   **`settings.yaml` (설정 파일)**: 회사별 근로 정책, 공휴일 정보, 상태 코드 매핑 등 모듈 운영에 필요한 모든 설정을 관리합니다.

### 2.1. 데이터 흐름

1.  사용자가 `cli.py`의 `calculate-hours` 명령어를 실행하며 입력 파일, 기간, 모드 등의 옵션을 전달합니다.
2.  `cli.py`는 `settings.yaml`(또는 지정된 설정 파일)에서 관련 설정을 로드합니다.
3.  로드된 설정과 함께 `WorkTimeProcessor` 인스턴스가 생성됩니다.
4.  `cli.py`는 입력 파일(CSV/JSON)을 읽어 `WorkTimeProcessor`가 처리할 수 있는 데이터 형식으로 변환합니다.
5.  `WorkTimeProcessor.process()` 메서드가 호출됩니다.
    *   `mode='auto'`인 경우, 입력 데이터 특성을 분석하여 `_detect_mode()`를 통해 처리 모드(attendance/timecard)를 결정합니다.
    *   결정된 모드에 따라 `AttendanceBasedCalculator` 또는 `TimeCardBasedCalculator`의 `calculate()` 메서드를 호출합니다.
6.  각 계산기는 전달받은 데이터와 설정을 기반으로 근로시간 관련 지표를 계산하고, 부분 결과를 반환합니다.
7.  `WorkTimeProcessor`는 계산기에서 반환된 부분 결과를 취합하여 `WorkTimeCalculationResult` 스키마에 따른 최종 통합 결과를 생성합니다.
8.  `cli.py`는 `WorkTimeCalculationResult`를 받아 사용자에게 표시(표준 출력)하거나 지정된 파일에 JSON 형식으로 저장합니다. 오류나 경고가 있을 경우 함께 출력합니다.

## 3. 핵심 모듈 상세 설명

### 3.1. `payslip/work_time_schema.py`

*   **역할**: 모듈 전체에서 사용되는 데이터 구조를 정의합니다. Pydantic 모델 또는 TypedDict를 사용하여 타입 안정성을 높이고, 데이터의 형식을 명확히 합니다.
*   **주요 정의**:
    *   `WorkTimeSettings`: `settings.yaml`에서 로드될 근로시간 관련 설정 구조.
    *   `AttendanceInputRecord`, `TimeCardInputRecord`: 각 모드별 입력 데이터 레코드 형식.
    *   `WorkSummary`, `TimeSummary`, `SalaryBasis`: 계산 결과의 주요 섹션별 구조.
    *   `ErrorDetail`: 오류 발생 시 상세 정보를 담는 구조.
    *   `WorkTimeCalculationResult`: 최종 통합 출력 구조.
*   **참고**: `work_time_schema_design.md` 문서에 상세 설계가 기술되어 있습니다.

### 3.2. `payslip/work_time_processor.py`

*   **역할**: 계산 모드 관리, 적절한 계산기 호출, 결과 통합 및 반환을 담당하는 컨트롤러 클래스입니다.
*   **주요 메서드**:
    *   `__init__(self, settings: WorkTimeSettings)`: 설정 객체를 받아 초기화합니다.
    *   `_detect_mode(...)`: 입력 데이터로부터 처리 모드를 자동 감지합니다.
    *   `process(...)`: 주 처리 로직으로, 입력 데이터와 파라미터를 받아 최종 `WorkTimeCalculationResult`를 반환합니다.
*   **특징**: 오류 처리, 로깅, 경고 메시지 관리 등 모듈의 안정적인 운영을 위한 중심 로직을 포함합니다.

### 3.3. `payslip/attendance_calculator.py`

*   **역할**: 출근 상태 기반(모드 A)의 근로시간 관련 지표를 계산합니다.
*   **주요 메서드**:
    *   `__init__(self, settings: WorkTimeSettings)`: 설정을 받아 초기화하며, 특히 `attendance_status_codes` 매핑 정보를 활용합니다.
    *   `calculate(self, attendance_data: List[AttendanceInputRecord], period_info: Dict)`: 출근 상태 데이터를 받아 `WorkSummary`와 `SalaryBasis`를 계산하여 반환합니다.
    *   내부적으로 해당 월의 총 일수, 소정근로일수 등을 계산하는 헬퍼 함수를 포함합니다.
*   **참고**: `TimeCardBasedCalculator`는 유사한 구조로 Plan 021에서 구현될 예정입니다.

## 4. CLI 사용법 (`calculate-hours`)

`cli_work_time_design.md` 문서에 상세히 기술된 바와 같이, `calculate-hours` 명령어를 통해 근로시간 계산 기능을 사용할 수 있습니다.

**기본 사용 예시:**

```bash
# 출근 상태 기반 데이터로 계산 (자동 모드 감지)
python cli.py calculate-hours --input-file data/attendance_202505.csv --period 2025-05 --output-file output/results_202505.json

# 모드 명시적 지정
python cli.py calculate-hours --input-file data/emp001_attendance.json --period 2025-05 --mode attendance --employee-id EMP001
```

**주요 옵션:**

*   `--input-file <PATH>` (필수): 입력 근태 데이터 파일 (CSV 또는 JSON).
*   `--period <YYYY-MM>` (필수): 처리 대상 연월.
*   `--mode <attendance|timecard|auto>` (선택, 기본값: `auto`): 계산 모드.
*   `--employee-id <ID>` (선택): 직원 ID.
*   `--output-file <PATH>` (선택): 결과 JSON 저장 경로 (미지정 시 표준 출력).
*   `--settings-file <PATH>` (선택): 사용자 정의 설정 파일 경로.

상세 옵션 및 설명은 `python cli.py calculate-hours --help`를 통해 확인할 수 있습니다.

## 5. 설정 (`settings.yaml`)

모듈의 동작은 `settings.yaml` 파일 내 `work_time_config` 섹션을 통해 제어됩니다. `cli_work_time_design.md`에 상세 구조 예시가 제공되어 있습니다.

**주요 설정 항목:**

*   `default_company_id`: 기본으로 사용할 회사 설정 ID.
*   `companies.<COMPANY_ID>`: 각 회사별 상세 설정.
    *   `default_daily_scheduled_hours`, `default_weekly_scheduled_hours`: 일/주 소정근로시간.
    *   `overtime_rules`, `night_work_rules`, `holiday_rules`: 연장/야간/휴일근로 가산율, 시간대, 공휴일 목록 등.
    *   `break_time_rules`: 근무시간에 따른 자동 휴게시간 부여 규칙.
    *   `attendance_status_codes`: 모드 A에서 사용될 출근 상태 코드와 그 의미(근무일수 값, 유/무급 여부, 지각/조퇴 여부 등) 매핑.

## 6. 오류 처리 및 로깅

*   **오류 처리**: 모든 예상 가능한 오류(파일 IO, 데이터 형식, 계산 로직 등)는 `try-except` 블록으로 처리되며, `WorkTimeCalculationResult`의 `error` 필드에 `ErrorDetail` 객체 형태로 상세 정보가 담겨 반환됩니다. CLI에서는 이 정보를 사용자 친화적으로 표시합니다.
*   **경고**: 데이터의 사소한 문제나 주의가 필요한 상황은 `warnings` 리스트에 문자열로 담겨 반환되며, CLI에서 사용자에게 알립니다.
*   **로깅**: `logging` 모듈을 사용하여 애플리케이션 전반의 이벤트(시작, 종료, 주요 파라미터, 오류, 경고 등)를 기록합니다. 로그 레벨(INFO, WARNING, ERROR, DEBUG)을 적절히 활용하며, `operation_logger`를 통해 통합 관리됩니다. 민감 정보 로깅 시 주의합니다.

## 7. 코드 스타일 및 주석

*   **코드 스타일**: PEP 8을 준수하여 작성합니다.
*   **주석 및 Docstrings**: 모든 클래스, 메서드, 주요 코드 블록에는 명확한 Docstring과 주석을 작성하여 코드의 가독성과 유지보수성을 높입니다. Docstring은 기능, 인자, 반환값 등을 명시합니다.
    *   예시 (메서드 Docstring):
        ```python
        def example_method(self, param1: str, param2: int) -> bool:
            """
            이 메서드는 예시 기능을 수행합니다.

            Args:
                param1: 첫 번째 인자에 대한 설명입니다.
                param2: 두 번째 인자에 대한 설명입니다.

            Returns:
                성공 시 True, 실패 시 False를 반환합니다.
            """
            # ... 로직 ...
        ```

## 8. 향후 개발 계획 (Plan 021 연계)

*   `TimeCardBasedCalculator` (모드 B) 상세 구현.
*   다양한 근로 유형(교대제, 간주근로 등) 및 복잡한 예외 케이스 처리 로직 강화.
*   급여 계산 모듈과의 직접적인 연동 인터페이스 개발.
*   웹 기반 UI에서의 활용을 위한 API 엔드포인트 설계.

이 문서는 지속적으로 업데이트될 예정입니다.
