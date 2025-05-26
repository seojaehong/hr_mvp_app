# 정책 기반 시뮬레이터 프로젝트

이 프로젝트는 한국 노동법에 기반한 근로시간 계산 및 급여 정책 시뮬레이션을 위한 도구입니다.

## 프로젝트 구조

```
/
├── app.py                      # Streamlit 기반 웹 인터페이스
├── cli/                        # 명령줄 인터페이스
│   ├── payroll_cli.py          # 급여 계산 CLI
│   └── policy_simulator_cli.py # 정책 시뮬레이터 CLI
├── docs/                       # 문서
│   ├── final_diagnostic_matrix.md
│   ├── plan_023_policy_based_structure.md
│   ├── plan_023_results_report.md
│   ├── plan_024_policy_simulator_objectives.md
│   └── policy_test_alignment_notes.md
├── enhanced_policy_scenarios.yaml     # 확장된 정책 시나리오 정의
├── enhanced_policy_scenarios_v2.yaml  # 확장된 정책 시나리오 정의 v2
├── holidays.yaml               # 공휴일 정의
├── Makefile                    # 자동화 스크립트
├── minimum_wage.yaml           # 최저임금 정의
├── output/                     # 출력 파일 저장 디렉토리
│   ├── logs/
│   ├── payroll/
│   └── payslips/
├── payslip/                    # 핵심 모듈
│   ├── attendance_calculator.py
│   ├── combination_runner.py   # 정책 조합 시뮬레이션
│   ├── compare_results.py      # 결과 비교 알고리즘
│   ├── enhanced_scenario_loader.py
│   ├── generator.py
│   ├── payslip_generator.py    # 급여명세서 생성
│   ├── policy_definitions.py   # 정책 정의
│   ├── policy_impact_analyzer.py
│   ├── policy_manager.py       # 정책 관리
│   ├── policy_simulator.py     # 정책 시뮬레이터
│   ├── policy_summary.py       # 정책 요약 및 시각화
│   ├── policy_template_generator.py
│   ├── scenario_loader.py      # 시나리오 로더
│   ├── security.py
│   ├── template_loader.py
│   ├── timecard_calculator.py  # 근무시간 계산
│   ├── timecard_calculator_refactored.py
│   ├── utils/                  # 유틸리티 함수
│   │   ├── formatter.py
│   │   └── validators.py
│   └── work_time_schema.py     # 근무시간 스키마
├── settings.yaml               # 설정 파일
├── templates/                  # 템플릿 파일
│   └── payslip_template.html   # 급여명세서 템플릿
└── tests/                      # 테스트
    ├── fixtures/               # 테스트 데이터
    │   ├── policy_scenarios.yaml
    │   └── timecard_cases.yaml
    ├── test_attendance_calculator.py
    ├── test_policy_based_calculation.py
    ├── test_timecard_calculator.py
    ├── test_utils.py
    └── test_work_time_processor.py
```

## 주요 기능

1. **정책 기반 근무시간 계산**
   - 다양한 근로시간 정책 적용 (연장근로, 야간근로, 휴일근로 등)
   - 한국 노동법 기반 계산 로직

2. **정책 시뮬레이션 및 비교**
   - 서로 다른 정책 간 결과 비교
   - 정책 조합 시뮬레이션
   - 최적 정책 추천

3. **시각화 및 보고서**
   - 정책 요약 보고서 생성
   - 비교 결과 시각화
   - 히트맵 및 차트 생성

4. **급여명세서 생성**
   - HTML/PDF 형식 명세서 생성
   - 커스텀 템플릿 지원

## 사용 방법

### 명령줄 인터페이스 (CLI)

```bash
# 단일 정책 시뮬레이션
python cli/policy_simulator_cli.py simulate --input tests/fixtures/timecard_cases.yaml --policy-set tests/fixtures/policy_scenarios.yaml --summary

# 정책 비교
python cli/policy_simulator_cli.py compare --input tests/fixtures/timecard_cases.yaml --policy-set1 tests/fixtures/policy_scenarios.yaml --policy-set2 enhanced_policy_scenarios.yaml

# 정책 조합 시뮬레이션
python cli/policy_simulator_cli.py combinations --input tests/fixtures/timecard_cases.yaml --options enhanced_policy_scenarios_v2.yaml
```

### Makefile 사용

```bash
# 테스트 실행
make test

# 단일 정책 시뮬레이션
make simulate

# 정책 비교
make compare

# 정책 조합 시뮬레이션
make combinations

# Streamlit 앱 실행
make streamlit
```

### Streamlit 웹 인터페이스

```bash
# Streamlit 앱 실행
streamlit run app.py
```

## 개발 환경 설정

1. 필요 패키지 설치:

```bash
pip install -r requirements.txt
```

2. 테스트 실행:

```bash
pytest tests/
```

## 라이선스

이 프로젝트는 내부 사용 목적으로 개발되었습니다.
