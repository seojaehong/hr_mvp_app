#!/usr/bin/env python3
"""
Streamlit 기반 정책 시뮬레이터 MVP

이 애플리케이션은 정책 시뮬레이터의 기능을 웹 인터페이스로 제공합니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go

# 상위 디렉토리를 모듈 검색 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from payslip.policy_simulator import PolicySimulator
from payslip.scenario_loader import ScenarioLoader
from payslip.policy_summary import generate_policy_summary, export_policy_summary_to_html
from payslip.compare_results import compare_worktime_outputs, visualize_worktime_diff
from payslip.combination_runner import (
    run_simulations_on_combinations, 
    generate_heatmap, 
    generate_policy_combination_matrix,
    filter_valid_combinations
)

# 페이지 설정
st.set_page_config(
    page_title="정책 시뮬레이터 MVP",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 사이드바 메뉴
st.sidebar.title("정책 시뮬레이터 MVP")
menu = st.sidebar.radio(
    "메뉴 선택",
    ["단일 정책 시뮬레이션", "정책 비교", "정책 조합 시뮬레이션", "명세서 생성"]
)

# 출력 디렉토리 설정
def setup_output_dir():
    """출력 디렉토리를 설정합니다."""
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # 타임스탬프 기반 하위 디렉토리 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = output_dir / f'run_{timestamp}'
    run_dir.mkdir(exist_ok=True)
    
    return run_dir

# 입력 데이터 로드
def load_input_data(uploaded_file):
    """업로드된 파일에서 입력 데이터를 로드합니다."""
    try:
        content = uploaded_file.read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        st.error(f"입력 파일 로드 중 오류 발생: {e}")
        return None

# 정책 세트 로드
def load_policy_set(uploaded_file):
    """업로드된 파일에서 정책 세트를 로드합니다."""
    try:
        content = uploaded_file.read().decode('utf-8')
        return json.loads(content)
    except Exception as e:
        st.error(f"정책 세트 파일 로드 중 오류 발생: {e}")
        return None

# 결과 시각화
def visualize_results(result):
    """시뮬레이션 결과를 시각화합니다."""
    if not result or "time_summary" not in result:
        st.warning("시각화할 결과가 없습니다.")
        return
    
    time_summary = result["time_summary"]
    
    # 시간 지표 차트
    time_metrics = {
        "regular_hours": "정규 근무시간",
        "overtime_hours": "연장 근무시간",
        "night_hours": "야간 근무시간",
        "holiday_hours": "휴일 근무시간"
    }
    
    time_data = {korean: time_summary.get(english, 0) for english, korean in time_metrics.items()}
    
    fig1 = px.pie(
        values=list(time_data.values()),
        names=list(time_data.keys()),
        title="근무시간 구성",
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig1)
    
    # 급여 지표 차트
    pay_metrics = {
        "base_pay": "기본급",
        "overtime_pay": "연장근로수당",
        "night_pay": "야간근로수당",
        "holiday_pay": "휴일근로수당"
    }
    
    pay_data = {korean: time_summary.get(english, 0) for english, korean in pay_metrics.items()}
    
    fig2 = px.bar(
        x=list(pay_data.keys()),
        y=list(pay_data.values()),
        title="급여 구성",
        labels={"x": "급여 항목", "y": "금액 (원)"},
        color=list(pay_data.keys()),
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig2)
    
    # 요약 테이블
    summary_data = {
        "총 근무일수": time_summary.get("work_days", 0),
        "총 근무시간": time_summary.get("total_hours", 0),
        "정규 근무시간": time_summary.get("regular_hours", 0),
        "연장 근무시간": time_summary.get("overtime_hours", 0),
        "야간 근무시간": time_summary.get("night_hours", 0),
        "휴일 근무시간": time_summary.get("holiday_hours", 0),
        "기본급": f"{time_summary.get('base_pay', 0):,}원",
        "연장근로수당": f"{time_summary.get('overtime_pay', 0):,}원",
        "야간근로수당": f"{time_summary.get('night_pay', 0):,}원",
        "휴일근로수당": f"{time_summary.get('holiday_pay', 0):,}원",
        "총 지급액": f"{time_summary.get('total_pay', 0):,}원"
    }
    
    df = pd.DataFrame(list(summary_data.items()), columns=["항목", "값"])
    st.table(df)

# 비교 결과 시각화
def visualize_comparison(comparison_data):
    """비교 결과를 시각화합니다."""
    if not comparison_data:
        st.warning("시각화할 비교 결과가 없습니다.")
        return
    
    # 시간 지표 비교 차트
    time_metrics = comparison_data.get("time_metrics", {})
    
    time_labels = []
    values1 = []
    values2 = []
    
    for metric, data in time_metrics.items():
        if metric in ["work_days", "total_hours", "regular_hours", "overtime_hours", "night_hours", "holiday_hours"]:
            # 지표명 한글화
            label = {
                "work_days": "근무일수",
                "total_hours": "총 근무시간",
                "regular_hours": "정규 근무시간",
                "overtime_hours": "연장 근무시간",
                "night_hours": "야간 근무시간",
                "holiday_hours": "휴일 근무시간"
            }.get(metric, metric)
            
            time_labels.append(label)
            values1.append(data.get("value1", 0))
            values2.append(data.get("value2", 0))
    
    fig1 = go.Figure(data=[
        go.Bar(name='정책 1', x=time_labels, y=values1),
        go.Bar(name='정책 2', x=time_labels, y=values2)
    ])
    
    fig1.update_layout(
        title="근무시간 비교",
        xaxis_title="지표",
        yaxis_title="시간",
        barmode='group'
    )
    
    st.plotly_chart(fig1)
    
    # 급여 지표 비교 차트
    pay_metrics = comparison_data.get("pay_metrics", {})
    
    pay_labels = []
    pay_values1 = []
    pay_values2 = []
    
    for metric, data in pay_metrics.items():
        # 지표명 한글화
        label = {
            "base_pay": "기본급",
            "overtime_pay": "연장근로수당",
            "night_pay": "야간근로수당",
            "holiday_pay": "휴일근로수당",
            "total_pay": "총 지급액"
        }.get(metric, metric)
        
        pay_labels.append(label)
        pay_values1.append(data.get("value1", 0))
        pay_values2.append(data.get("value2", 0))
    
    fig2 = go.Figure(data=[
        go.Bar(name='정책 1', x=pay_labels, y=pay_values1),
        go.Bar(name='정책 2', x=pay_labels, y=pay_values2)
    ])
    
    fig2.update_layout(
        title="급여 비교",
        xaxis_title="지표",
        yaxis_title="금액 (원)",
        barmode='group'
    )
    
    st.plotly_chart(fig2)
    
    # 중요한 차이점
    st.subheader("중요한 차이점")
    
    significant_diffs = comparison_data.get("significant_differences", [])
    if significant_diffs:
        for diff in significant_diffs:
            diff_percent = diff.get("diff_percent", 0)
            if diff_percent > 0:
                st.success(diff.get("description", ""))
            else:
                st.error(diff.get("description", ""))
    else:
        st.info("중요한 차이점이 없습니다.")
    
    # 정책 차이점
    st.subheader("정책 변경 사항")
    
    policy_diffs = comparison_data.get("policy_differences", [])
    if policy_diffs:
        for diff in policy_diffs:
            change_type = diff.get("change_type", "")
            policy = diff.get("policy", "")
            description = diff.get("description", "")
            
            if change_type == "added":
                st.success(f"{policy} (추가됨): {description}")
            elif change_type == "removed":
                st.error(f"{policy} (제거됨): {description}")
            elif change_type == "modified":
                st.info(f"{policy} (변경됨): {description}")
                
                # 설정 변경 사항 테이블
                setting_diffs = diff.get("setting_differences", [])
                if setting_diffs:
                    setting_data = []
                    for setting_diff in setting_diffs:
                        setting_data.append({
                            "설정": setting_diff.get("setting", ""),
                            "정책 1 값": setting_diff.get("value1", ""),
                            "정책 2 값": setting_diff.get("value2", "")
                        })
                    
                    st.table(pd.DataFrame(setting_data))
    else:
        st.info("정책 변경 사항이 없습니다.")

# 히트맵 시각화
def visualize_heatmap(heatmap_data):
    """히트맵 데이터를 시각화합니다."""
    if not heatmap_data or "heatmaps" not in heatmap_data:
        st.warning("시각화할 히트맵 데이터가 없습니다.")
        return
    
    heatmaps = heatmap_data.get("heatmaps", {})
    
    # 지표 선택
    metrics = list(heatmaps.keys())
    selected_metric = st.selectbox(
        "지표 선택",
        metrics,
        format_func=lambda x: {
            "total_hours": "총 근무시간",
            "overtime_hours": "연장 근무시간",
            "night_hours": "야간 근무시간",
            "holiday_hours": "휴일 근무시간",
            "base_pay": "기본급",
            "overtime_pay": "연장근로수당",
            "night_pay": "야간근로수당",
            "holiday_pay": "휴일근로수당",
            "total_pay": "총 지급액"
        }.get(x, x)
    )
    
    if selected_metric in heatmaps:
        heatmap = heatmaps[selected_metric]
        
        policy_sets = heatmap.get("policy_sets", [])
        values = heatmap.get("values", [])
        
        if policy_sets and values:
            # 히트맵 생성
            fig = go.Figure(data=go.Heatmap(
                z=[values],
                x=policy_sets,
                colorscale='Viridis',
                showscale=True
            ))
            
            fig.update_layout(
                title=f"{selected_metric} 히트맵",
                xaxis_title="정책 세트",
                yaxis_title="",
                height=400
            )
            
            st.plotly_chart(fig)
            
            # 값 테이블
            data = []
            for i, policy_set in enumerate(policy_sets):
                if i < len(values):
                    data.append({
                        "정책 세트": policy_set,
                        "값": values[i]
                    })
            
            df = pd.DataFrame(data)
            st.table(df)

# 단일 정책 시뮬레이션 페이지
def single_simulation_page():
    st.title("단일 정책 시뮬레이션")
    
    # 파일 업로드
    st.subheader("입력 파일 업로드")
    input_file = st.file_uploader("입력 데이터 파일 (JSON)", type=["json"], key="single_input")
    policy_file = st.file_uploader("정책 세트 파일 (JSON)", type=["json"], key="single_policy")
    
    if input_file and policy_file:
        # 데이터 로드
        input_data = load_input_data(input_file)
        policy_set = load_policy_set(policy_file)
        
        if input_data and policy_set:
            # 시뮬레이션 실행 버튼
            if st.button("시뮬레이션 실행"):
                with st.spinner("시뮬레이션 실행 중..."):
                    # 출력 디렉토리 설정
                    output_dir = setup_output_dir()
                    
                    # 시뮬레이터 초기화 및 실행
                    simulator = PolicySimulator()
                    result = simulator.simulate(input_data, policy_set)
                    
                    # 결과 저장
                    result_file = output_dir / 'simulation_result.json'
                    with open(result_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    # 정책 요약 생성 및 저장
                    policy_summary = generate_policy_summary(result)
                    summary_file = output_dir / 'policy_summary.json'
                    with open(summary_file, 'w', encoding='utf-8') as f:
                        json.dump(policy_summary, f, ensure_ascii=False, indent=2)
                    
                    # HTML 요약 생성
                    html_summary_file = output_dir / 'policy_summary.html'
                    export_policy_summary_to_html(policy_summary, str(html_summary_file))
                    
                    st.success(f"시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
                    
                    # 결과 시각화
                    st.subheader("시뮬레이션 결과")
                    visualize_results(result)
                    
                    # 결과 파일 다운로드
                    with open(result_file, 'r', encoding='utf-8') as f:
                        result_json = f.read()
                    
                    st.download_button(
                        label="결과 JSON 다운로드",
                        data=result_json,
                        file_name="simulation_result.json",
                        mime="application/json"
                    )
                    
                    # HTML 요약 다운로드
                    with open(html_summary_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    st.download_button(
                        label="HTML 요약 다운로드",
                        data=html_content,
                        file_name="policy_summary.html",
                        mime="text/html"
                    )

# 정책 비교 페이지
def policy_comparison_page():
    st.title("정책 비교")
    
    # 파일 업로드
    st.subheader("입력 파일 업로드")
    input_file = st.file_uploader("입력 데이터 파일 (JSON)", type=["json"], key="compare_input")
    policy_file1 = st.file_uploader("정책 세트 1 파일 (JSON)", type=["json"], key="compare_policy1")
    policy_file2 = st.file_uploader("정책 세트 2 파일 (JSON)", type=["json"], key="compare_policy2")
    
    if input_file and policy_file1 and policy_file2:
        # 데이터 로드
        input_data = load_input_data(input_file)
        policy_set1 = load_policy_set(policy_file1)
        policy_set2 = load_policy_set(policy_file2)
        
        if input_data and policy_set1 and policy_set2:
            # 비교 실행 버튼
            if st.button("비교 실행"):
                with st.spinner("정책 비교 실행 중..."):
                    # 출력 디렉토리 설정
                    output_dir = setup_output_dir()
                    
                    # 시뮬레이터 초기화 및 실행
                    simulator = PolicySimulator()
                    result1 = simulator.simulate(input_data, policy_set1)
                    result2 = simulator.simulate(input_data, policy_set2)
                    
                    # 결과 저장
                    result1_file = output_dir / 'result1.json'
                    result2_file = output_dir / 'result2.json'
                    
                    with open(result1_file, 'w', encoding='utf-8') as f:
                        json.dump(result1, f, ensure_ascii=False, indent=2)
                    
                    with open(result2_file, 'w', encoding='utf-8') as f:
                        json.dump(result2, f, ensure_ascii=False, indent=2)
                    
                    # 비교 결과 생성
                    comparison = compare_worktime_outputs(result1, result2)
                    
                    # 비교 결과 저장
                    comparison_file = output_dir / 'comparison.json'
                    with open(comparison_file, 'w', encoding='utf-8') as f:
                        json.dump(comparison, f, ensure_ascii=False, indent=2)
                    
                    # HTML 비교 결과 생성
                    html_comparison_file = output_dir / 'comparison.html'
                    export_comparison_to_html(comparison, str(html_comparison_file))
                    
                    st.success(f"정책 비교 완료. 결과가 {output_dir}에 저장되었습니다.")
                    
                    # 비교 결과 시각화
                    st.subheader("비교 결과")
                    visualize_comparison(comparison)
                    
                    # 결과 파일 다운로드
                    with open(comparison_file, 'r', encoding='utf-8') as f:
                        comparison_json = f.read()
                    
                    st.download_button(
                        label="비교 결과 JSON 다운로드",
                        data=comparison_json,
                        file_name="comparison_result.json",
                        mime="application/json"
                    )
                    
                    # HTML 비교 결과 다운로드
                    with open(html_comparison_file, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    
                    st.download_button(
                        label="HTML 비교 결과 다운로드",
                        data=html_content,
                 
(Content truncated due to size limit. Use line ranges to read in chunks)