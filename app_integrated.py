#!/usr/bin/env python3
"""
Streamlit 기반 HR MVP 애플리케이션

근로시간 계산, 정책 시뮬레이션, 급여 명세서 생성 기능을 제공합니다.
"""
import sys
import os
import streamlit as st
import pandas as pd
import numpy as np
import json
from datetime import datetime
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, Union, Type
from pydantic import BaseModel
import logging

# --- 로깅 설정 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 프로젝트 경로 설정 ---
project_root_path = os.path.dirname(os.path.abspath(__file__))
if project_root_path not in sys.path:
    sys.path.insert(0, project_root_path)

# --- 모듈 임포트 ---
try:
    # 근로시간 계산 모듈
    from Payslip.Worktime.schema import (
        WorkTimeCalculationResult, AttendanceInputData, TimeCardInputData,
        AttendanceInputRecord, TimeCardRecord, ErrorDetails
    )
    from Payslip.Worktime.processor import WorkTimeProcessor
    from Payslip.Worktime.calculator import TimeCardBasedCalculator
    from Payslip.Worktime.attendance import AttendanceBasedCalculator

    # 정책 시뮬레이터 관련 모듈 (기존 기능 유지)
    from Payslip.policy_simulator import PolicySimulator

    # 급여 계산 및 명세서 생성 모듈
    from Payslip.payslip_generator import PayslipGenerator, PayslipCalculator
    from Payslip.policy_manager import PolicyManager

except ImportError as e:
    st.error(f"필수 모듈 로딩 실패: {e}. Payslip 패키지 구조와 경로를 확인하세요.")
    st.stop()

# --- 페이지 설정 ---
st.set_page_config(
    page_title="HR MVP 애플리케이션",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 기본 설정 (하드코딩 또는 파일 로드) ---
# 실제 운영 시에는 settings.yaml 등에서 로드하는 것이 좋습니다.
DEFAULT_SETTINGS = {
    "company_id": "DEFAULT_COMP",
    "company_settings": {
        "daily_work_minutes_standard": 480,
        "weekly_work_minutes_standard": 2400,
        "night_shift_start_time": "22:00",
        "night_shift_end_time": "06:00",
        "break_time_rules": [
            {"threshold_minutes": 240, "break_minutes": 30},
            {"threshold_minutes": 480, "break_minutes": 60}
        ]
    },
    "attendance_status_codes": {
        "1": {"work_day_value": 1.0, "is_paid_leave": False, "is_unpaid_leave": False, "description": "정상 출근"},
        "2": {"work_day_value": 0.0, "is_paid_leave": False, "is_unpaid_leave": True, "description": "결근"},
        "3": {"work_day_value": 1.0, "is_paid_leave": True, "is_unpaid_leave": False, "description": "유급 휴가"},
        "4": {"work_day_value": 0.0, "is_paid_leave": False, "is_unpaid_leave": True, "description": "무급 휴가"},
        "5": {"work_day_value": 0.5, "is_paid_leave": False, "is_unpaid_leave": False, "description": "반차"}
    },
    "company_info": {
        "company_name": "테스트 회사",
        "business_registration_number": "000-00-00000",
        "ceo_name": "홍길동",
        "company_address": "서울시",
        "company_contact": "02-123-4567"
    },
    "payslip_template": {
        "template_dir": "templates",
        "template_name": "payslip_template.html",
        "calculation_message_if_missing": "계산식이 제공되지 않았습니다."
    }
}

# --- 유틸리티 함수 ---
def setup_output_dir(sub_dir_name="streamlit_outputs"):
    """출력 디렉토리를 설정합니다."""
    output_dir = Path('output') / sub_dir_name
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = output_dir / f'run_{timestamp}'
    run_dir.mkdir(exist_ok=True)
    return run_dir

def load_yaml_or_json(uploaded_file):
    """업로드된 YAML 또는 JSON 파일에서 데이터를 로드합니다."""
    if uploaded_file is None:
        return None
    try:
        content = uploaded_file.read().decode('utf-8')
        file_type = uploaded_file.type.split('/')[-1]
        if file_type == 'yaml':
            import yaml
            return yaml.safe_load(content)
        else: # json
            return json.loads(content)
    except Exception as e:
        st.error(f"파일 로드 중 오류 발생 ({uploaded_file.name}): {e}")
        return None

def safe_model_dump(model_instance):
    """Pydantic 모델을 안전하게 dict로 변환합니다."""
    if hasattr(model_instance, 'model_dump'):
        return model_instance.model_dump()
    elif isinstance(model_instance, dict):
        return model_instance
    elif isinstance(model_instance, list):
        return [safe_model_dump(item) for item in model_instance]
    else:
        try:
            # 기본 __dict__ 시도
            return vars(model_instance)
        except TypeError:
            # 변환 불가 시 문자열로 반환
            return str(model_instance)

# --- 결과 시각화 함수 ---
def display_worktime_results(result: WorkTimeCalculationResult):
    """근로시간 계산 결과를 Streamlit에 표시합니다."""
    if not result:
        st.warning("표시할 결과가 없습니다.")
        return

    st.subheader("처리 요약")
    col1, col2 = st.columns(2)
    col1.metric("처리 모드", result.processing_mode if result.processing_mode else "N/A")
    col2.metric("직원 ID", result.employee_id if result.employee_id else "N/A")

    if result.error:
        st.error(f"오류 발생: {result.error.error_code} - {result.error.message}")
        if result.error.details:
            st.caption(f"상세 정보: {result.error.details}")
        return # 오류 발생 시 추가 정보 표시 중단

    if result.warnings:
        st.subheader("경고")
        for warning in result.warnings:
            st.warning(warning)

    if result.attendance_summary:
        st.subheader("출결 요약 (모드 A)")
        summary = result.attendance_summary
        data = {
            "항목": ["총 기간 일수", "예정 근무일수", "실제 근무일수", "전일 근무일수", "유급 휴가일수", "무급 휴가일수"],
            "값": [
                summary.total_days_in_period,
                summary.scheduled_work_days,
                summary.actual_work_days,
                summary.full_work_days,
                summary.paid_leave_days,
                summary.unpaid_leave_days
            ]
        }
        st.table(pd.DataFrame(data))

    if result.salary_basis:
        st.subheader("급여 계산 기준 (모드 A)")
        basis = result.salary_basis
        data = {
            "항목": ["급여 지급 대상 일수", "공제 대상 일수"],
            "값": [basis.payment_target_days, basis.deduction_days]
        }
        st.table(pd.DataFrame(data))

    if result.time_summary:
        st.subheader("시간 요약 (모드 B)")
        summary = result.time_summary
        data = {
            "항목": ["정규 근무시간(H)", "연장 근무시간(H)", "야간 근무시간(H)", "휴일 근무시간(H)", "총 실근로시간(H)", "총 유급시간(H)", "총 근무시간(H)"],
            "값": [
                summary.regular_hours,
                summary.overtime_hours,
                summary.night_hours,
                summary.holiday_hours,
                summary.total_net_work_hours,
                summary.total_paid_hours,
                summary.total_work_hours
            ]
        }
        st.table(pd.DataFrame(data))

    if result.daily_calculation_details:
        st.subheader("일별 계산 상세 (모드 B)")
        try:
            df_daily = pd.DataFrame([safe_model_dump(detail) for detail in result.daily_calculation_details])
            st.dataframe(df_daily)
        except Exception as e:
            st.error(f"일별 상세 정보 표시 중 오류: {e}")
            st.json(safe_model_dump(result.daily_calculation_details))

    if result.compliance_alerts:
        st.subheader("컴플라이언스 알림")
        for alert in result.compliance_alerts:
            alert_dict = safe_model_dump(alert)
            message = alert_dict.get('message', '')
            severity = alert_dict.get('severity', 'info')
            if severity == "error":
                st.error(message)
            elif severity == "warning":
                st.warning(message)
            else:
                st.info(message)

# --- 페이지별 로직 ---

def work_time_calculation_page():
    st.title("근로시간 자동 계산")
    st.write("직원의 출결 기록 또는 타임카드를 기반으로 근로시간을 계산합니다.")

    # 입력 모드 선택
    calc_mode = st.radio("계산 모드 선택", ("출결 기반 (모드 A)", "타임카드 기반 (모드 B)"), key="worktime_mode")
    selected_mode = "attendance" if calc_mode == "출결 기반 (모드 A)" else "timecard"

    # 파일 업로드
    input_file = st.file_uploader(f"{calc_mode} 입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="worktime_input")

    if input_file:
        input_data_dict = load_yaml_or_json(input_file)

        if input_data_dict:
            st.subheader("입력 데이터 미리보기 (처음 5개 레코드)")
            records_preview = input_data_dict.get('records', [])[:5]
            if records_preview:
                st.json(records_preview)
            else:
                st.info("입력 파일에 'records' 데이터가 없거나 비어있습니다.")

            employee_id = st.text_input("직원 ID (선택 사항)", value=input_data_dict.get('employee_id', ''))
            period = st.text_input("계산 기간 (YYYY-MM)", value=input_data_dict.get('period', datetime.now().strftime("%Y-%m")))

            if st.button("근로시간 계산 실행", key="run_worktime_calc"):
                with st.spinner("근로시간 계산 중..."):
                    try:
                        # WorkTimeProcessor 초기화 (기본 설정 사용)
                        processor = WorkTimeProcessor(settings=DEFAULT_SETTINGS)

                        # 입력 데이터 준비 (records만 추출)
                        input_records = input_data_dict.get('records', [])
                        if not input_records:
                            st.error("입력 파일에 'records' 데이터가 없습니다.")
                            st.stop()

                        # processor.process 호출
                        result = processor.process(
                            input_data=input_records,
                            period=period,
                            employee_id=employee_id if employee_id else None,
                            mode=selected_mode
                        )

                        st.success("근로시간 계산 완료.")
                        st.subheader("계산 결과")
                        display_worktime_results(result)

                        # 결과 다운로드 버튼
                        result_dict = safe_model_dump(result)
                        st.download_button(
                            label="결과 JSON 다운로드",
                            data=json.dumps(result_dict, ensure_ascii=False, indent=2, default=str),
                            file_name=f"worktime_result_{employee_id}_{period.replace('-', '')}.json",
                            mime="application/json"
                        )

                    except Exception as e:
                        logger.exception("근로시간 계산 중 오류 발생")
                        st.error(f"근로시간 계산 중 예상치 못한 오류 발생: {e}")

def single_simulation_page():
    st.title("단일 정책 시뮬레이션")
    st.write("하나의 입력 데이터와 하나의 정책 세트를 사용하여 시뮬레이션을 실행합니다.")
    st.info("참고: 이 기능은 현재 타임카드 기반 데이터만 지원합니다.")

    # 파일 업로드
    input_file = st.file_uploader("타임카드 입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="single_input")
    policy_file = st.file_uploader("정책 세트 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="single_policy")

    if input_file and policy_file:
        input_data_dict = load_yaml_or_json(input_file)
        policy_set_dict = load_yaml_or_json(policy_file)

        if input_data_dict and policy_set_dict:
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
                    period=input_data_dict.get('period', datetime.now().strftime("%Y-%m")),
                    hire_date=hire_date_obj,
                    resignation_date=resignation_date_obj,
                    records=records
                )
            except Exception as e:
                st.error(f"입력 데이터를 TimeCardInputData 객체로 변환 중 오류: {e}")
                input_data_obj = None

            if input_data_obj and st.button("시뮬레이션 실행", key="run_single_sim"):
                with st.spinner("시뮬레이션 실행 중..."):
                    try:
                        output_dir = setup_output_dir("single_simulation")
                        simulator = PolicySimulator(settings=policy_set_dict) # 정책을 설정으로 전달
                        result = simulator.simulate(input_data_obj) # 입력 데이터만 전달

                        st.success(f"시뮬레이션 완료.")
                        st.subheader("시뮬레이션 결과 (근로시간)")
                        display_worktime_results(result) # 근로시간 결과 표시

                        # 결과 저장 및 다운로드
                        result_dict = safe_model_dump(result)
                        result_file = output_dir / 'simulation_result.json'
                        with open(result_file, 'w', encoding='utf-8') as f:
                            json.dump(result_dict, f, ensure_ascii=False, indent=2, default=str)
                        st.info(f"결과가 {result_file}에 저장되었습니다.")
                        st.download_button(
                            label="결과 JSON 다운로드",
                            data=json.dumps(result_dict, ensure_ascii=False, indent=2, default=str),
                            file_name="simulation_result.json",
                            mime="application/json"
                        )
                    except Exception as e:
                        logger.exception("단일 정책 시뮬레이션 중 오류 발생")
                        st.error(f"시뮬레이션 중 예상치 못한 오류 발생: {e}")

def payslip_generation_page():
    st.title("급여 계산 및 명세서 생성")
    st.write("직원의 근무 기록을 바탕으로 급여를 계산하고 명세서를 생성합니다.")
    st.info("참고: 이 기능은 현재 타임카드 기반 데이터만 지원합니다.")

    # 입력 파일 (TimeCardInputData 형식의 JSON 또는 YAML)
    input_file = st.file_uploader("타임카드 입력 데이터 파일 (JSON 또는 YAML)", type=["json", "yaml"], key="payslip_input")
    # 정책 파일 (선택 사항)
    policy_file = st.file_uploader("적용할 정책 세트 파일 (JSON 또는 YAML, 선택 사항)", type=["json", "yaml"], key="payslip_policy")

    if input_file:
        input_data_dict = load_yaml_or_json(input_file)

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
                policy_set_dict = load_yaml_or_json(policy_file)
                if policy_set_dict:
                    try:
                        # PolicyManager에 로드된 정책 적용
                        for key, value in policy_set_dict.items():
                            policy_manager.set(key, value)
                        st.info("사용자 정의 정책 세트가 적용되었습니다.")
                    except Exception as e:
                        st.error(f"정책 파일 적용 중 오류: {e}")

            if timecard_input_data and st.button("급여 계산 및 명세서 생성", key="run_payslip"):
                with st.spinner("급여 계산 및 명세서 생성 중..."):
                    try:
                        output_dir = setup_output_dir("payslips")

                        # PayslipCalculator 사용
                        calculator = PayslipCalculator(policy_manager=policy_manager)
                        payroll_data_dict = calculator.calculate_payslip(timecard_input_data)

                        # 결과 JSON 저장
                        payroll_json_file = output_dir / f"{timecard_input_data.employee_id}_{timecard_input_data.period.replace('-', '')}_payroll.json"
                        with open(payroll_json_file, 'w', encoding='utf-8') as f:
                            json.dump(payroll_data_dict, f, ensure_ascii=False, indent=2, default=str)
                        st.success(f"급여 계산 완료. JSON 결과: {payroll_json_file}")

                        # PayslipGenerator 설정
                        company_info = DEFAULT_SETTINGS.get("company_info", {})
                        template_settings = DEFAULT_SETTINGS.get("payslip_template", {})
                        template_dir_path = Path(template_settings.get("template_dir", "templates"))
                        template_name = template_settings.get("template_name", "payslip_template.html")

                        if not (template_dir_path / template_name).is_file():
                            st.error(f"급여명세서 HTML 템플릿 파일을 찾을 수 없습니다: {template_dir_path / template_name}")
                            st.stop()

                        generator = PayslipGenerator(
                            company_info=company_info,
                            template_dir=str(template_dir_path.resolve()),
                            template_name=template_name,
                            calculation_message_if_missing=template_settings.get("calculation_message_if_missing", "")
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

                    except Exception as e:
                        logger.exception("급여 계산/명세서 생성 중 오류 발생")
                        st.error(f"급여 계산/명세서 생성 중 예상치 못한 오류 발생: {e}")

# --- 메인 실행 로직 ---
if __name__ == "__main__":
    st.sidebar.title("HR MVP")
    menu_options = [
        "근로시간 자동 계산",
        "단일 정책 시뮬레이션",
        "급여 계산 및 명세서 생성"
    ]
    menu = st.sidebar.radio("메뉴 선택", menu_options)

    if menu == menu_options[0]:
        work_time_calculation_page()
    elif menu == menu_options[1]:
        single_simulation_page()
    elif menu == menu_options[2]:
        payslip_generation_page()
