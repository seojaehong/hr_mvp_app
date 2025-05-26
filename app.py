#!/usr/bin/env python3
"""
Streamlit 기반 정책 시뮬레이터 MVP

이 애플리케이션은 정책 시뮬레이터의 기능을 웹 인터페이스로 제공합니다.
"""
import sys # 맨 위에 한 번만
import os  # 맨 위에 한 번만

# 현재 app.py 파일이 있는 폴더의 경로를 가져옵니다.
# 이 경로가 바로 우리 프로젝트의 기본 경로가 됩니다.
project_root_path = os.path.dirname(os.path.abspath(__file__))

# 만약 이 경로가 파이썬이 파일을 찾는 경로 목록에 없다면 추가해 줍니다.
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path) # <<< 여기 들여쓰기를 추가했어요!

import streamlit as st
import pandas as pd
import numpy as np
import json
# import os # 중복이므로 삭제
# import sys # 중복이므로 삭제
from datetime import datetime
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# --- Payslip 패키지에서 필요한 모듈 가져오기 ---
from Payslip.policy_simulator import PolicySimulator # "payslip" (p 소문자)
from Payslip.scenario_loader import EnhancedScenarioLoader # ScenarioLoader -> EnhancedScenarioLoader로 변경
from Payslip.policy_summary import generate_policy_summary, export_policy_summary_to_html

#from Payslip.compare_results import CompareResults, export_comparison_to_html

from Payslip.combination_runner import (
    run_simulations_on_combinations,
    generate_heatmap,
    generate_policy_combination_matrix,
    filter_valid_combinations,
    export_simulation_results_to_html,
    export_simulation_results_to_json
)
from Payslip.payslip_generator import PayslipGenerator, PayslipCalculator
from Payslip.work_time_schema import TimeCardInputData, TimeCardRecord
from Payslip.policy_manager import PolicyManager

# 페이지 설정
st.set_page_config(
    page_title="정책 시뮬레이터 MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 메뉴
st.sidebar.title("정책 시뮬레이터 MVP")
menu_options = ["단일 정책 시뮬레이션", "정책 비교", "정책 조합 시뮬레이션", "급여 계산 및 명세서 생성"]
menu = st.sidebar.radio(
    "메뉴 선택",
    menu_options
)

# 출력 디렉토리 설정
def setup_output_dir(sub_dir_name="streamlit_outputs"):
    """출력 디렉토리를 설정합니다."""
    output_dir = Path('output') / sub_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = output_dir / f'run_{timestamp}'
    run_dir.mkdir(exist_ok=True)
    return run_dir

# 입력 데이터 로드 (YAML 또는 JSON)
def load_yaml_or_json(uploaded_file, file_type='json'):
    """업로드된 YAML 또는 JSON 파일에서 데이터를 로드합니다."""
    if uploaded_file is None:
        return None
    try:
        content = uploaded_file.read().decode('utf-8')
        if file_type == 'yaml':
            import yaml
            return yaml.safe_load(content)
        else: # json
            return json.loads(content)
    except Exception as e:
        st.error(f"{file_type.upper()} 파일 로드 중 오류 발생: {e}")
        return None

# --- 결과 시각화 함수들 (기존 _archive/app.py 내용 활용) ---
def visualize_results(result):
    """시뮬레이션 결과를 시각화합니다."""
    if not result or "time_summary" not in result:
        st.warning("시각화할 결과가 없습니다.")
        return

    time_summary = result.get("time_summary", {}) # .get()으로 안전하게 접근

    st.subheader("시간 요약")
    time_metrics_data = []
    for key, value in time_summary.items():
        if isinstance(value, (int, float, str)): # 숫자나 문자열만 표시
             time_metrics_data.append({"항목": key, "값": value})
    if time_metrics_data:
        st.table(pd.DataFrame(time_metrics_data))
    else:
        st.info("시간 요약 정보가 결과에 없습니다.")

    # 일별 계산 상세 정보 (있는 경우)
    daily_details = result.get("daily_calculation_details")
    if daily_details:
        st.subheader("일별 계산 상세")
        try:
            # WorkDayDetail 객체를 dict로 변환 (필요시)
            df_daily = pd.DataFrame([detail.model_dump() if hasattr(detail, 'model_dump') else detail for detail in daily_details])
            st.dataframe(df_daily)
        except Exception as e:
            st.error(f"일별 상세 정보 표시 중 오류: {e}")
            st.json(daily_details) # 오류 시 JSON으로 표시

    warnings = result.get("warnings", [])
    if warnings:
        st.subheader("경고")
        for warning in warnings:
            st.warning(warning)

    compliance_alerts = result.get("compliance_alerts", [])
    if compliance_alerts:
        st.subheader("컴플라이언스 알림")
        for alert in compliance_alerts:
             # ComplianceAlert 객체라면 속성 접근, dict라면 키 접근
            message = alert.message if hasattr(alert, 'message') else alert.get('message', '')
            severity = alert.severity if hasattr(alert, 'severity') else alert.get('severity', 'info')
            if severity == "error":
                st.error(message)
            elif severity == "warning":
                st.warning(message)
            else:
                st.info(message)

def visualize_comparison(comparison_data):
    """비교 결과를 시각화합니다."""
    if not comparison_data:
        st.warning("시각화할 비교 결과가 없습니다.")
        return

    # 시간 지표 비교
    st.subheader("시간 지표 비교")
    time_metrics = comparison_data.get("time_metrics", {})
    if time_metrics:
        df_time_metrics = pd.DataFrame(time_metrics).T.reset_index()
        df_time_metrics.columns = ['항목', '정책1 값', '정책2 값', '차이', '변화율(%)']
        st.table(df_time_metrics)
    else:
        st.info("시간 지표 비교 정보가 없습니다.")

    # 급여 지표 비교 (만약 있다면)
    pay_metrics = comparison_data.get("pay_metrics", {})
    if pay_metrics:
        st.subheader("급여 지표 비교")
        df_pay_metrics = pd.DataFrame(pay_metrics).T.reset_index()
        df_pay_metrics.columns = ['항목', '정책1 값', '정책2 값', '차이', '변화율(%)']
        st.table(df_pay_metrics)

    # 중요한 차이점
    st.subheader("중요한 차이점")
    significant_diffs = comparison_data.get("significant_differences", [])
    if significant_diffs:
        for diff in significant_diffs:
            st.write(f"- {diff.get('description', '')} (정책1: {diff.get('value1')}, 정책2: {diff.get('value2')})")
    else:
        st.info("중요한 차이점이 없습니다.")

    # 정책 차이점
    st.subheader("정책 변경 사항")
    policy_diffs = comparison_data.get("policy_differences", [])
    if policy_diffs:
        for diff in policy_diffs:
            st.write(f"- 정책 '{diff.get('policy', '')}': {diff.get('description', '')}")
            if "setting_differences" in diff:
                st.table(pd.DataFrame(diff["setting_differences"]))
    else:
        st.info("정책 변경 사항이 없습니다.")


def visualize_combination_results(simulation_results):
    """정책 조합 시뮬레이션 결과를 시각화합니다."""
    if not simulation_results or "results" not in simulation_results:
        st.warning("시각화할 조합 시뮬레이션 결과가 없습니다.")
        return

    results_list = simulation_results.get("results", [])
    display_data = []

    for item in results_list:
        policy_set_info = item.get("policy_set", {})
        result_data = item.get("result", {})
        time_summary = result_data.get("time_summary", {}) if isinstance(result_data, dict) else {}

        # TimeSummary 객체라면 .get() 대신 속성 접근 필요
        if hasattr(time_summary, 'total_net_work_hours'): # TimeSummary 객체인지 확인
            total_hours = time_summary.total_net_work_hours
            # 다른 필요한 값들도 동일하게 접근
        else: # dict인 경우
            total_hours = time_summary.get("total_net_work_hours", 0)


        row = {
            "정책 조합명": policy_set_info.get("name", "N/A"),
            # 필요한 다른 정책 정보 추가 가능
            "총 순 근로시간": float(total_hours) if total_hours is not None else 0,
            # "총 급여": float(time_summary.get("total_pay", 0)) # 급여 항목 추가 시
        }
        display_data.append(row)

    if display_data:
        df_display = pd.DataFrame(display_data)
        st.dataframe(df_display)

        # 히트맵 시각화 (예시: 총 순 근로시간 기준)
        if not df_display.empty and "총 순 근로시간" in df_display.columns:
            st.subheader("정책 조합별 총 순 근로시간 히트맵")
            # 히트맵은 정책 조합이 많을 때 유용, 여기서는 간단히 바 차트로 대체 가능
            fig = px.bar(df_display, x="정책 조합명", y="총 순 근로시간", title="정책 조합별 총 순 근로시간")
            st.plotly_chart(fig)
    else:
        st.info("표시할 결과 데이터가 없습니다.")

    # HTML 결과 파일 다운로드 버튼
    output_dir = setup_output_dir("combination_outputs")
    html_results_file = output_dir / 'simulation_results.html'
    if export_simulation_results_to_html(simulation_results, str(html_results_file)):
        with open(html_results_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        st.download_button(
            label="조합 시뮬레이션 HTML 보고서 다운로드",
            data=html_content,
            file_name="combination_simulation_report.html",
            mime="text/html"
        )
    json_results_file = output_dir / 'simulation_results.json'
    if export_simulation_results_to_json(simulation_results, str(json_results_file)):
        with open(json_results_file, 'r', encoding='utf-8') as f:
            json_content = f.read()
        st.download_button(
            label="조합 시뮬레이션 JSON 결과 다운로드",
            data=json_content,
            file_name="combination_simulation_results.json",
            mime="application/json"
        )

# --- 페이지별 로직 ---

def single_simulation_page():
    st.title("단일 정책 시뮬레이션")
    st.write("하나의 입력 데이터와 하나의 정책 세트를 사용하여 시뮬레이션을 실행합니다.")

    # 파일 업로드
    input_file = st.file_uploader("입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="single_input")
    policy_file = st.file_uploader("정책 세트 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="single_policy")

    if input_file and policy_file:
        input_data_dict = load_yaml_or_json(input_file, file_type=input_file.type.split('/')[-1])
        policy_set_dict = load_yaml_or_json(policy_file, file_type=policy_file.type.split('/')[-1])

        if input_data_dict and policy_set_dict:
            # TimeCardInputData 객체로 변환
            # 입력 파일이 timecard_cases.yaml의 'input' 필드 형식이라고 가정
            try:
                # records 변환
                records = []
                for record_data in input_data_dict.get('records', []):
                    date_str = record_data.get('date')
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                    records.append(TimeCardRecord(
                        date=date_obj,
                        start_time=record_data.get('start_time'),
                        end_time=record_data.get('end_time'),
                        break_time_minutes=record_data.get('break_time_minutes', 0)
                        # is_holiday 필드는 policy_manager가 처리하므로 여기서는 생략 가능
                    ))
                hire_date_str = input_data_dict.get('hire_date')
                hire_date_obj = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
                resignation_date_str = input_data_dict.get('resignation_date')
                resignation_date_obj = datetime.strptime(resignation_date_str, '%Y-%m-%d').date() if resignation_date_str else None

                input_data_obj = TimeCardInputData(
                    employee_id=input_data_dict.get('employee_id', 'N/A'),
                    period=input_data_dict.get('period', 'N/A'),
                    hire_date=hire_date_obj,
                    resignation_date=resignation_date_obj,
                    records=records
                )
            except Exception as e:
                st.error(f"입력 데이터를 TimeCardInputData 객체로 변환 중 오류: {e}")
                input_data_obj = None

            if input_data_obj and st.button("시뮬레이션 실행", key="run_single_sim"):
                with st.spinner("시뮬레이션 실행 중..."):
                    output_dir = setup_output_dir("single_simulation")
                    simulator = PolicySimulator() # PolicyManager는 Simulator 내부에서 생성/관리
                    # PolicySimulator의 simulate 메서드는 policy_set을 dict로 받음
                    result = simulator.simulate(input_data_obj, policy_set_dict) # policy_set_dict를 직접 전달

                    # 결과가 WorkTimeCalculationResult 객체이므로 dict로 변환하여 저장/표시
                    result_dict = result.model_dump() if hasattr(result, 'model_dump') else result


                    result_file = output_dir / 'simulation_result.json'
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str) # default=str 추가

                    st.success(f"시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
                    st.subheader("시뮬레이션 결과")
                    visualize_results(result_dict) # dict 전달

                    # 다운로드 버튼
                    st.download_button(
                        label="결과 JSON 다운로드",
                        data=json.dumps(result_dict, ensure_ascii=False, indent=2, default=str),
                        file_name="simulation_result.json",
                        mime="application/json"
                    )
                    # 정책 요약 (선택적)
                    # policy_summary = generate_policy_summary(result_dict)
                    # html_summary_file = output_dir / 'policy_summary.html'
                    # export_policy_summary_to_html(policy_summary, str(html_summary_file))


def policy_comparison_page():
    st.title("정책 비교")
    st.write("하나의 입력 데이터에 대해 두 가지 다른 정책 세트를 적용하여 결과를 비교합니다.")

    input_file = st.file_uploader("입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="compare_input")
    policy_file1 = st.file_uploader("정책 세트 1 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="compare_policy1")
    policy_file2 = st.file_uploader("정책 세트 2 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="compare_policy2")

    if input_file and policy_file1 and policy_file2:
        input_data_dict = load_yaml_or_json(input_file, file_type=input_file.type.split('/')[-1])
        policy_set1_dict = load_yaml_or_json(policy_file1, file_type=policy_file1.type.split('/')[-1])
        policy_set2_dict = load_yaml_or_json(policy_file2, file_type=policy_file2.type.split('/')[-1])

        if input_data_dict and policy_set1_dict and policy_set2_dict:
            # TimeCardInputData 객체로 변환
            try:
                records = []
                for record_data in input_data_dict.get('records', []):
                    date_str = record_data.get('date')
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                    records.append(TimeCardRecord(
                        date=date_obj,
                        start_time=record_data.get('start_time'),
                        end_time=record_data.get('end_time'),
                        break_time_minutes=record_data.get('break_time_minutes', 0)
                    ))
                hire_date_str = input_data_dict.get('hire_date')
                hire_date_obj = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
                resignation_date_str = input_data_dict.get('resignation_date')
                resignation_date_obj = datetime.strptime(resignation_date_str, '%Y-%m-%d').date() if resignation_date_str else None

                input_data_obj = TimeCardInputData(
                    employee_id=input_data_dict.get('employee_id', 'N/A'),
                    period=input_data_dict.get('period', 'N/A'),
                    hire_date=hire_date_obj,
                    resignation_date=resignation_date_obj,
                    records=records
                )
            except Exception as e:
                st.error(f"입력 데이터를 TimeCardInputData 객체로 변환 중 오류: {e}")
                input_data_obj = None

            if input_data_obj and st.button("비교 실행", key="run_compare"):
                with st.spinner("정책 비교 실행 중..."):
                    output_dir = setup_output_dir("policy_comparison")
                    simulator = PolicySimulator()
                    result1 = simulator.simulate(input_data_obj, policy_set1_dict)
                    result2 = simulator.simulate(input_data_obj, policy_set2_dict)

                    # 결과 객체를 dict로 변환
                    result1_dict = result1.model_dump() if hasattr(result1, 'model_dump') else result1
                    result2_dict = result2.model_dump() if hasattr(result2, 'model_dump') else result2

                    comparison = compare_worktime_outputs(result1_dict, result2_dict) # dict 전달

                    comparison_file = output_dir / 'comparison.json'
                    with open(comparison_file, 'w', encoding='utf-8') as f:
                        json.dump(comparison, f, ensure_ascii=False, indent=2, default=str)

                    html_comparison_file = output_dir / 'comparison_report.html'
                    export_comparison_to_html(comparison, str(html_comparison_file)) # 이 함수가 dict를 받는지 확인

                    st.success(f"정책 비교 완료. 결과가 {output_dir}에 저장되었습니다.")
                    st.subheader("비교 결과")
                    visualize_comparison(comparison) # dict 전달

                    st.download_button(
                        label="비교 결과 JSON 다운로드",
                        data=json.dumps(comparison, ensure_ascii=False, indent=2, default=str),
                        file_name="comparison.json",
                        mime="application/json"
                    )
                    with open(html_comparison_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    st.download_button(
                        label="HTML 비교 보고서 다운로드",
                        data=html_content,
                        file_name="comparison_report.html",
                        mime="text/html"
                    )

def combination_simulation_page():
    st.title("정책 조합 시뮬레이션")
    st.write("여러 정책 옵션들의 조합을 만들어 각 조합에 대한 시뮬레이션을 실행하고 결과를 비교합니다.")

    input_file = st.file_uploader("입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="combo_input")
    # 정책 옵션 파일은 enhanced_policy_scenarios_v2.yaml 같은 복잡한 구조를 가질 수 있음
    policy_options_file = st.file_uploader("정책 옵션 파일 (YAML, 시나리오 파일 형식)", type=["yaml"], key="combo_options")

    if input_file and policy_options_file:
        input_data_dict = load_yaml_or_json(input_file, file_type=input_file.type.split('/')[-1])
        # 정책 옵션 파일은 ScenarioLoader를 통해 로드하는 것이 적합할 수 있음
        # 여기서는 간단히 YAML로 로드하지만, 실제로는 ScenarioLoader의 policy_sets 등을 활용해야 할 수 있음
        # 또는 policy_options_file 자체가 조합 생성 로직에 맞는 특정 포맷을 가져야 함.
        # combination_runner.generate_policy_combination_matrix가 받는 policy_options는
        # {'카테고리1': [{'name': '옵션A', ...}, {'name': '옵션B', ...}], '카테고리2': [...]} 형태여야 함.
        # 이 포맷에 맞게 사용자가 파일을 준비하거나, 여기서 변환 로직이 필요.
        # 지금은 파일 내용을 그대로 policy_options로 가정.
        raw_policy_options_data = load_yaml_or_json(policy_options_file, file_type='yaml')

        # ScenarioLoader를 사용하여 policy_sets 추출 (enhanced_policy_scenarios_v2.yaml 파일 기준)
        # 실제 사용 시에는 ScenarioLoader를 통해 policy_sets 등을 가져오는 것이 더 적합
        # 여기서는 임시로 policy_sets를 직접 추출한다고 가정
        policy_options_for_matrix = {}
        if raw_policy_options_data and "policy_sets" in raw_policy_options_data:
             # 예시: 첫번째 policy_set의 policies를 옵션으로 사용 (실제로는 더 정교한 로직 필요)
             # generate_policy_combination_matrix는 특정 구조의 dict를 기대하므로,
             # enhanced_policy_scenarios_v2.yaml의 policy_sets를 직접 사용할 수 없음.
             # 사용자에게 policy_options 형태의 파일을 업로드하도록 안내하거나,
             # ScenarioLoader로 로드한 후 적절히 가공해야 함.
             # 지금은 policy_options_file 자체가 generate_policy_combination_matrix에 맞는다고 가정.
             # 이 부분은 실제 policy_options_file의 구조에 따라 수정 필요.
            st.warning("정책 옵션 파일의 구조가 generate_policy_combination_matrix 함수에 적합해야 합니다.")
            # policy_options_for_matrix = raw_policy_options_data # 직접 사용 시도 (파일 구조가 맞아야 함)
            # 임시로, enhanced_policy_scenarios_v2.yaml의 policy_schema를 사용해 가상 policy_options 생성
            if "policy_schema" in raw_policy_options_data:
                temp_options = {}
                for key, schema_info in raw_policy_options_data["policy_schema"].items():
                    category = schema_info.get("category", "default_category")
                    if category not in temp_options:
                        temp_options[category] = []

                    # 옵션 값 생성 (default, 또는 enum이 있으면 enum 값들)
                    option_values = []
                    if "validation" in schema_info and schema_info["validation"].get("type") == "enum":
                        option_values.extend(schema_info["validation"].get("allowed_values", []))
                    else:
                        option_values.append(schema_info.get("default")) # 기본값만 사용

                    for val in option_values:
                        if val is not None: # None이 아닌 값만 옵션으로 추가
                             temp_options[category].append({"name": f"{key}_{val}", "config": {key: val}}) # 정책 적용을 위한 config 추가
                policy_options_for_matrix = temp_options
            else:
                st.error("정책 옵션 파일에서 'policy_schema'를 찾을 수 없습니다. 조합 생성을 위한 옵션 구성이 어렵습니다.")
                policy_options_for_matrix = None
        else:
            policy_options_for_matrix = None
            st.error("정책 옵션 파일 로드 실패 또는 내용이 부적합합니다.")


        if input_data_dict and policy_options_for_matrix:
            # TimeCardInputData 객체로 변환
            try:
                records = []
                for record_data in input_data_dict.get('records', []):
                    date_str = record_data.get('date')
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                    records.append(TimeCardRecord(
                        date=date_obj,
                        start_time=record_data.get('start_time'),
                        end_time=record_data.get('end_time'),
                        break_time_minutes=record_data.get('break_time_minutes', 0)
                    ))
                hire_date_str = input_data_dict.get('hire_date')
                hire_date_obj = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
                resignation_date_str = input_data_dict.get('resignation_date')
                resignation_date_obj = datetime.strptime(resignation_date_str, '%Y-%m-%d').date() if resignation_date_str else None

                input_data_obj = TimeCardInputData(
                    employee_id=input_data_dict.get('employee_id', 'N/A'),
                    period=input_data_dict.get('period', 'N/A'),
                    hire_date=hire_date_obj,
                    resignation_date=resignation_date_obj,
                    records=records
                )
            except Exception as e:
                st.error(f"입력 데이터를 TimeCardInputData 객체로 변환 중 오류: {e}")
                input_data_obj = None


            if input_data_obj and st.button("조합 시뮬레이션 실행", key="run_combo_sim"):
                with st.spinner("정책 조합 생성 및 시뮬레이션 실행 중..."):
                    output_dir = setup_output_dir("combination_simulation")

                    # generate_policy_combination_matrix는 각 카테고리별 옵션 리스트를 받음
                    # 각 옵션은 name과 실제 정책 설정을 포함하는 dict여야 함
                    # policy_options_for_matrix는 {'category': [{'name':'opt1', 'config':{...}}, ...]} 형태여야 함
                    raw_combinations = generate_policy_combination_matrix(policy_options_for_matrix)
                    
                    # generate_policy_combination_matrix의 결과는 {'name': 'A+B', 'policies': [optA_dict, optB_dict]} 형태
                    # run_simulations_on_combinations에 전달할 policy_combinations는
                    # 각 요소가 실제 정책 설정 dict (예: {'calculation_mode.simple_mode': True, ...}) 여야 함
                    
                    policy_combinations_for_runner = []
                    for combo in raw_combinations:
                        actual_policies = {}
                        # 'policies'는 옵션 dict의 리스트. 각 옵션 dict에서 'config'를 가져와 병합
                        for option_dict in combo.get('policies', []):
                            actual_policies.update(option_dict.get('config', {}))
                        # 조합의 이름도 전달하기 위해 policy_set 형태로 구성
                        policy_combinations_for_runner.append({
                            "name": combo.get("name", "Unnamed Combination"),
                            "policies": actual_policies # 실제 정책 설정
                        })

                    # filter_valid_combinations는 현재 로직상 의미가 없을 수 있음 (충돌 정의가 policy_options_for_matrix에 없음)
                    # valid_combinations = filter_valid_combinations(raw_combinations) # 이 함수는 현재 로직과 맞지 않음
                    valid_combinations_for_runner = policy_combinations_for_runner # 일단 모든 조합을 유효하다고 가정

                    st.write(f"생성된 정책 조합 수: {len(valid_combinations_for_runner)}")
                    if not valid_combinations_for_runner:
                        st.error("실행할 유효한 정책 조합이 없습니다.")
                        return

                    # run_simulations_on_combinations의 두 번째 인자는 List[Dict[str, Any]] 형태 (각 dict가 하나의 정책 세트)
                    # 위에서 policy_combinations_for_runner를 만들 때, 각 요소가 {'name': ..., 'policies': {...실제 정책 설정...}} 형태이므로
                    # 여기서 'policies' 값만 추출해서 리스트로 만들어야 함.
                    # 또는 run_simulations_on_combinations 함수가 {'name': ..., 'policies': ...} 형태를 받도록 수정 필요.
                    # 현재 combination_runner.py의 run_simulations_on_combinations는
                    # policy_combinations: List[Dict[str, Any]] 를 받아서 각 Dict를 policy_set으로 사용함.
                    # 따라서 policy_combinations_for_runner의 각 요소에서 'policies' 키의 값(실제 정책 설정 dict)을 전달해야 함.

                    actual_policy_sets_to_run = [combo['policies'] for combo in valid_combinations_for_runner]
                    # 이름을 함께 전달하고 싶다면, run_simulations_on_combinations 결과에 이름을 매핑할 방법 필요
                    # 여기서는 PolicySimulator가 policy_set 이름을 자동으로 생성하지 않으므로,
                    # run_simulations_on_combinations의 결과를 후처리하거나, 해당 함수 수정 필요.
                    # 임시로, 결과에 policy_set의 이름을 추가하는 로직이 combination_runner에 있다고 가정하고 진행.
                    # 또는 PolicySimulator.simulate_across_policies를 직접 사용 고려.

                    simulation_results = run_simulations_on_combinations(
                        input_data_obj, # TimeCardInputData 객체 전달
                        actual_policy_sets_to_run, # 실제 정책 설정 리스트 전달
                        max_workers=4
                    )
                    # simulation_results의 'results' 각 항목에 policy_set 이름을 매칭시켜주는 작업이 필요할 수 있음
                    # (현재 combination_runner.run_simulations_on_combinations는 반환값에 입력 policy_set 정보를 포함함)

                    st.success(f"조합 시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
                    st.subheader("조합 시뮬레이션 결과 요약")
                    visualize_combination_results(simulation_results)


def payslip_generation_page():
    st.title("급여 계산 및 명세서 생성")
    st.write("직원의 근무 기록을 바탕으로 급여를 계산하고 명세서를 생성합니다.")

    # 입력 파일 (TimeCardInputData 형식의 JSON 또는 YAML)
    input_file = st.file_uploader("타임카드 입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="payslip_input")
    # 정책 파일 (선택 사항, 기본 정책을 사용하거나 특정 정책을 적용할 수 있도록)
    policy_file = st.file_uploader("적용할 정책 세트 파일 (JSON 또는 YAML, 선택 사항)", type=["json", "yaml"], key="payslip_policy")

    if input_file:
        input_data_dict = load_yaml_or_json(input_file, file_type=input_file.type.split('/')[-1])

        if input_data_dict:
            # TimeCardInputData 객체로 변환
            try:
                records = []
                for record_data in input_data_dict.get('records', []):
                    date_str = record_data.get('date')
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else None
                    records.append(TimeCardRecord(
                        date=date_obj,
                        start_time=record_data.get('start_time'),
                        end_time=record_data.get('end_time'),
                        break_time_minutes=record_data.get('break_time_minutes', 0)
                    ))
                hire_date_str = input_data_dict.get('hire_date')
                hire_date_obj = datetime.strptime(hire_date_str, '%Y-%m-%d').date() if hire_date_str else None
                resignation_date_str = input_data_dict.get('resignation_date')
                resignation_date_obj = datetime.strptime(resignation_date_str, '%Y-%m-%d').date() if resignation_date_str else None

                timecard_input_data = TimeCardInputData(
                    employee_id=input_data_dict.get('employee_id', 'N/A'),
                    period=input_data_dict.get('period', datetime.now().strftime("%Y-%m")),
                    hire_date=hire_date_obj,
                    resignation_date=resignation_date_obj,
                    records=records
                )
            except Exception as e:
                st.error(f"타임카드 입력 데이터를 객체로 변환 중 오류: {e}")
                timecard_input_data = None

            # 정책 설정
            policy_manager = PolicyManager() # 기본 설정으로 초기화
            if policy_file:
                policy_set_dict = load_yaml_or_json(policy_file, file_type=policy_file.type.split('/')[-1])
                if policy_set_dict:
                    # PolicyManager에 로드된 정책 적용 (set 메서드 활용)
                    for key, value in policy_set_dict.items(): # policy_set_dict가 플랫한 키-값 쌍이라고 가정
                        policy_manager.set(key, value)
                    st.info("사용자 정의 정책 세트가 적용되었습니다.")

            if timecard_input_data and st.button("급여 계산 및 명세서 생성", key="run_payslip"):
                with st.spinner("급여 계산 및 명세서 생성 중..."):
                    output_dir = setup_output_dir("payslips")

                    # PayslipCalculator 사용
                    calculator = PayslipCalculator(policy_manager=policy_manager)
                    # calculate_payslip은 payroll_data (dict)를 반환
                    payroll_data_dict = calculator.calculate_payslip(timecard_input_data)

                    # 결과 JSON 저장
                    payroll_json_file = output_dir / f"{timecard_input_data.employee_id}_{timecard_input_data.period.replace('-', '')}_payroll.json"
                    with open(payroll_json_file, 'w', encoding='utf-8') as f:
                        json.dump(payroll_data_dict, f, ensure_ascii=False, indent=2, default=str)
                    st.success(f"급여 계산 완료. JSON 결과: {payroll_json_file}")

                    # PayslipGenerator 설정 (settings.yaml 값 사용 또는 기본값)
                    # 이 부분은 payroll_cli.py의 설정 로직 참고
                    # settings = load_settings() # payroll_cli.py 처럼 설정 로드 필요
                    # 지금은 하드코딩된 값으로 대체
                    company_info = {"company_name": "테스트 회사", "business_registration_number": "000-00-00000",
                                    "ceo_name": "홍길동", "company_address": "서울시", "company_contact":"02-123-4567"}
                    template_dir_path = Path("templates") # 프로젝트 루트의 templates 폴더
                    template_name = "payslip_template.html" # templates 폴더 안의 파일명

                    if not (template_dir_path / template_name).is_file():
                        st.error(f"급여명세서 HTML 템플릿 파일을 찾을 수 없습니다: {template_dir_path / template_name}")
                        return

                    generator = PayslipGenerator(
                        company_info=company_info,
                        template_dir=str(template_dir_path.resolve()), # 절대 경로로
                        template_name=template_name,
                        calculation_message_if_missing="계산식이 제공되지 않았습니다."
                        # settings = settings # 전체 설정 전달 시
                    )

                    # PDF 생성
                    pdf_filename = f"{timecard_input_data.employee_id}_{timecard_input_data.period.replace('-', '')}_payslip.pdf"
                    pdf_path = output_dir / pdf_filename
                    success_pdf, error_msg_pdf = generator.generate_pdf(payroll_data_dict, str(pdf_path))

                    if success_pdf:
                        st.success(f"PDF 급여명세서 생성 완료: {pdf_path}")
                        with open(pdf_path, "rb") as pdf_file_content:
                            st.download_button(
                                label="PDF 급여명세서 다운로드",
                                data=pdf_file_content,
                                file_name=pdf_filename,
                                mime="application/pdf"
                            )
                    else:
                        st.error(f"PDF 급여명세서 생성 실패: {error_msg_pdf}")

                    # HTML 미리보기 (선택적)
                    html_content = generator.generate_html(payroll_data_dict)
                    if html_content:
                        st.subheader("HTML 급여명세서 미리보기")
                        st.components.v1.html(html_content, height=600, scrolling=True)
                        html_filename = f"{timecard_input_data.employee_id}_{timecard_input_data.period.replace('-', '')}_payslip.html"
                        html_path = output_dir / html_filename
                        with open(html_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        st.info(f"HTML 급여명세서 저장됨: {html_path}")


# --- 메인 실행 로직 ---
if __name__ == "__main__":
    # sys.path 설정이 올바른지, Payslip 패키지가 현재 위치에서 import 가능한지 확인
    # st.write(sys.path) # 경로 확인용

    if menu == menu_options[0]: # 단일 정책 시뮬레이션
        single_simulation_page()
    elif menu == menu_options[1]: # 정책 비교
        policy_comparison_page()
    elif menu == menu_options[2]: # 정책 조합 시뮬레이션
        combination_simulation_page()
    elif menu == menu_options[3]: # 급여 계산 및 명세서 생성
        payslip_generation_page()