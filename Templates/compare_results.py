"""
결과 비교 및 시각화 모듈

이 모듈은 서로 다른 정책 간 계산 결과를 비교하고 시각화하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def compare_worktime_outputs(result1: Dict[str, Any], result2: Dict[str, Any]) -> Dict[str, Any]:
    """
    두 근무시간 계산 결과를 비교합니다.
    
    Args:
        result1: 첫 번째 계산 결과
        result2: 두 번째 계산 결과
        
    Returns:
        비교 결과
    """
    # 비교 결과 초기화
    comparison = {
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "result1_id": result1.get("metadata", {}).get("id", "unknown"),
            "result2_id": result2.get("metadata", {}).get("id", "unknown"),
            "result1_policy_set": result1.get("metadata", {}).get("policy_set", "unknown"),
            "result2_policy_set": result2.get("metadata", {}).get("policy_set", "unknown")
        },
        "time_metrics": {},
        "pay_metrics": {},
        "significant_differences": [],
        "policy_differences": []
    }
    
    # 시간 지표 비교
    time_summary1 = result1.get("time_summary", {})
    time_summary2 = result2.get("time_summary", {})
    
    time_metrics = [
        "work_days", "total_hours", "regular_hours", "overtime_hours", 
        "night_hours", "holiday_hours", "late_hours", "absent_days"
    ]
    
    for metric in time_metrics:
        value1 = time_summary1.get(metric, 0)
        value2 = time_summary2.get(metric, 0)
        diff = value2 - value1
        diff_percent = (diff / value1 * 100) if value1 != 0 else float('inf')
        
        comparison["time_metrics"][metric] = {
            "value1": value1,
            "value2": value2,
            "diff": diff,
            "diff_percent": diff_percent
        }
        
        # 중요한 차이점 식별 (10% 이상 차이나는 경우)
        if abs(diff_percent) >= 10 and metric != "absent_days":
            comparison["significant_differences"].append({
                "metric": metric,
                "diff": diff,
                "diff_percent": diff_percent,
                "description": f"{metric}이(가) {abs(diff_percent):.1f}% {'증가' if diff > 0 else '감소'}"
            })
    
    # 급여 지표 비교
    pay_metrics = [
        "base_pay", "overtime_pay", "night_pay", "holiday_pay", "total_pay"
    ]
    
    for metric in pay_metrics:
        value1 = time_summary1.get(metric, 0)
        value2 = time_summary2.get(metric, 0)
        diff = value2 - value1
        diff_percent = (diff / value1 * 100) if value1 != 0 else float('inf')
        
        comparison["pay_metrics"][metric] = {
            "value1": value1,
            "value2": value2,
            "diff": diff,
            "diff_percent": diff_percent
        }
        
        # 중요한 차이점 식별 (5% 이상 차이나는 경우)
        if abs(diff_percent) >= 5:
            comparison["significant_differences"].append({
                "metric": metric,
                "diff": diff,
                "diff_percent": diff_percent,
                "description": f"{metric}이(가) {abs(diff_percent):.1f}% {'증가' if diff > 0 else '감소'}"
            })
    
    # 정책 차이점 분석
    policies1 = result1.get("applied_policies", [])
    policies2 = result2.get("applied_policies", [])
    
    # 정책 이름 추출
    policy_names1 = {p.get("name"): p for p in policies1}
    policy_names2 = {p.get("name"): p for p in policies2}
    
    # 결과1에만 있는 정책
    for name, policy in policy_names1.items():
        if name not in policy_names2:
            comparison["policy_differences"].append({
                "policy": name,
                "change_type": "removed",
                "description": f"정책 '{name}'이(가) 제거됨",
                "details": policy
            })
    
    # 결과2에만 있는 정책
    for name, policy in policy_names2.items():
        if name not in policy_names1:
            comparison["policy_differences"].append({
                "policy": name,
                "change_type": "added",
                "description": f"정책 '{name}'이(가) 추가됨",
                "details": policy
            })
    
    # 양쪽 다 있지만 내용이 다른 정책
    for name, policy1 in policy_names1.items():
        if name in policy_names2:
            policy2 = policy_names2[name]
            if policy1 != policy2:
                # 정책 설정값 비교
                setting_diffs = []
                for key in set(policy1.keys()) | set(policy2.keys()):
                    if key in policy1 and key in policy2:
                        if policy1[key] != policy2[key]:
                            setting_diffs.append({
                                "setting": key,
                                "value1": policy1[key],
                                "value2": policy2[key]
                            })
                    elif key in policy1:
                        setting_diffs.append({
                            "setting": key,
                            "value1": policy1[key],
                            "value2": None
                        })
                    else:
                        setting_diffs.append({
                            "setting": key,
                            "value1": None,
                            "value2": policy2[key]
                        })
                
                comparison["policy_differences"].append({
                    "policy": name,
                    "change_type": "modified",
                    "description": f"정책 '{name}'의 설정이 변경됨",
                    "setting_differences": setting_diffs
                })
    
    return comparison

def generate_diff_table(comparison: Dict[str, Any]) -> pd.DataFrame:
    """
    비교 결과를 테이블 형태로 변환합니다.
    
    Args:
        comparison: 비교 결과
        
    Returns:
        비교 결과 테이블
    """
    # 시간 및 급여 지표 통합
    all_metrics = {}
    all_metrics.update(comparison.get("time_metrics", {}))
    all_metrics.update(comparison.get("pay_metrics", {}))
    
    # 테이블 데이터 구성
    table_data = []
    
    # 지표명 한글화 매핑
    metric_names = {
        "work_days": "근무일수",
        "total_hours": "총 근무시간",
        "regular_hours": "정규 근무시간",
        "overtime_hours": "연장 근무시간",
        "night_hours": "야간 근무시간",
        "holiday_hours": "휴일 근무시간",
        "late_hours": "지각 시간",
        "absent_days": "결근일수",
        "base_pay": "기본급",
        "overtime_pay": "연장근로수당",
        "night_pay": "야간근로수당",
        "holiday_pay": "휴일근로수당",
        "total_pay": "총 지급액"
    }
    
    # 단위 매핑
    metric_units = {
        "work_days": "일",
        "total_hours": "시간",
        "regular_hours": "시간",
        "overtime_hours": "시간",
        "night_hours": "시간",
        "holiday_hours": "시간",
        "late_hours": "시간",
        "absent_days": "일",
        "base_pay": "원",
        "overtime_pay": "원",
        "night_pay": "원",
        "holiday_pay": "원",
        "total_pay": "원"
    }
    
    # 카테고리 매핑
    metric_categories = {
        "work_days": "근무시간",
        "total_hours": "근무시간",
        "regular_hours": "근무시간",
        "overtime_hours": "근무시간",
        "night_hours": "근무시간",
        "holiday_hours": "근무시간",
        "late_hours": "근무시간",
        "absent_days": "근무시간",
        "base_pay": "급여",
        "overtime_pay": "급여",
        "night_pay": "급여",
        "holiday_pay": "급여",
        "total_pay": "급여"
    }
    
    for metric, values in all_metrics.items():
        # 중요 차이점 여부 확인
        is_significant = False
        for diff in comparison.get("significant_differences", []):
            if diff.get("metric") == metric:
                is_significant = True
                break
        
        # 값 포맷팅
        value1 = values.get("value1", 0)
        value2 = values.get("value2", 0)
        diff = values.get("diff", 0)
        diff_percent = values.get("diff_percent", 0)
        
        # 단위 추가
        unit = metric_units.get(metric, "")
        
        # 테이블 행 추가
        table_data.append({
            "카테고리": metric_categories.get(metric, "기타"),
            "지표": metric_names.get(metric, metric),
            "정책1 값": f"{value1:,} {unit}",
            "정책2 값": f"{value2:,} {unit}",
            "차이": f"{diff:+,} {unit}",
            "변화율": f"{diff_percent:+.1f}%",
            "중요 차이": "예" if is_significant else "아니오"
        })
    
    # 데이터프레임 생성
    if table_data:
        df = pd.DataFrame(table_data)
        # 카테고리별 정렬
        return df.sort_values(by=["카테고리", "지표"])
    else:
        return pd.DataFrame(columns=["카테고리", "지표", "정책1 값", "정책2 값", "차이", "변화율", "중요 차이"])

def visualize_worktime_diff(result_a: Dict[str, Any], result_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    두 근무시간 계산 결과의 차이를 시각화하기 위한 데이터를 생성합니다.
    
    Args:
        result_a: 첫 번째 계산 결과
        result_b: 두 번째 계산 결과
        
    Returns:
        시각화 데이터
    """
    # 비교 결과 계산
    comparison = compare_worktime_outputs(result_a, result_b)
    
    # 시각화 데이터 초기화
    visualization_data = {
        "metadata": {
            "result_a_id": comparison["metadata"]["result1_id"],
            "result_b_id": comparison["metadata"]["result2_id"],
            "result_a_policy_set": comparison["metadata"]["result1_policy_set"],
            "result_b_policy_set": comparison["metadata"]["result2_policy_set"],
            "timestamp": comparison["timestamp"]
        },
        "time_metrics_chart": {
            "labels": [],
            "result_a_values": [],
            "result_b_values": [],
            "diff_percentages": []
        },
        "pay_metrics_chart": {
            "labels": [],
            "result_a_values": [],
            "result_b_values": [],
            "diff_percentages": []
        },
        "significant_differences": comparison["significant_differences"],
        "policy_changes": []
    }
    
    # 시간 지표 차트 데이터
    time_metrics_korean = {
        "work_days": "근무일수",
        "total_hours": "총 근무시간",
        "regular_hours": "정규 근무시간",
        "overtime_hours": "연장 근무시간",
        "night_hours": "야간 근무시간",
        "holiday_hours": "휴일 근무시간"
    }
    
    for metric, korean_name in time_metrics_korean.items():
        if metric in comparison["time_metrics"]:
            values = comparison["time_metrics"][metric]
            visualization_data["time_metrics_chart"]["labels"].append(korean_name)
            visualization_data["time_metrics_chart"]["result_a_values"].append(values["value1"])
            visualization_data["time_metrics_chart"]["result_b_values"].append(values["value2"])
            visualization_data["time_metrics_chart"]["diff_percentages"].append(values["diff_percent"])
    
    # 급여 지표 차트 데이터
    pay_metrics_korean = {
        "base_pay": "기본급",
        "overtime_pay": "연장근로수당",
        "night_pay": "야간근로수당",
        "holiday_pay": "휴일근로수당",
        "total_pay": "총 지급액"
    }
    
    for metric, korean_name in pay_metrics_korean.items():
        if metric in comparison["pay_metrics"]:
            values = comparison["pay_metrics"][metric]
            visualization_data["pay_metrics_chart"]["labels"].append(korean_name)
            visualization_data["pay_metrics_chart"]["result_a_values"].append(values["value1"])
            visualization_data["pay_metrics_chart"]["result_b_values"].append(values["value2"])
            visualization_data["pay_metrics_chart"]["diff_percentages"].append(values["diff_percent"])
    
    # 정책 변경 요약
    for diff in comparison["policy_differences"]:
        change_type = diff["change_type"]
        policy_name = diff["policy"]
        
        if change_type == "added":
            visualization_data["policy_changes"].append({
                "policy": policy_name,
                "change_type": "추가",
                "description": f"정책 '{policy_name}'이(가) 추가됨"
            })
        elif change_type == "removed":
            visualization_data["policy_changes"].append({
                "policy": policy_name,
                "change_type": "제거",
                "description": f"정책 '{policy_name}'이(가) 제거됨"
            })
        elif change_type == "modified":
            setting_changes = []
            for setting_diff in diff.get("setting_differences", []):
                setting = setting_diff["setting"]
                value1 = setting_diff["value1"]
                value2 = setting_diff["value2"]
                setting_changes.append(f"{setting}: {value1} → {value2}")
            
            visualization_data["policy_changes"].append({
                "policy": policy_name,
                "change_type": "변경",
                "description": f"정책 '{policy_name}'의 설정이 변경됨",
                "details": setting_changes
            })
    
    return visualization_data

def highlight_policy_diff(policy_a: Dict[str, Any], policy_b: Dict[str, Any]) -> Dict[str, Any]:
    """
    두 정책 간의 차이점을 강조합니다.
    
    Args:
        policy_a: 첫 번째 정책
        policy_b: 두 번째 정책
        
    Returns:
        차이점이 강조된 정책 정보
    """
    # 결과 초기화
    diff_result = {
        "policy_a_name": policy_a.get("name", "정책 A"),
        "policy_b_name": policy_b.get("name", "정책 B"),
        "common_settings": [],
        "different_settings": [],
        "only_in_a": [],
        "only_in_b": []
    }
    
    # 모든 설정 키 수집
    all_keys = set(policy_a.keys()) | set(policy_b.keys())
    
    # 설정별 비교
    for key in all_keys:
        # 양쪽 다 있는 설정
        if key in policy_a and key in policy_b:
            if policy_a[key] == policy_b[key]:
                diff_result["common_settings"].append({
                    "key": key,
                    "value": policy_a[key]
                })
            else:
                diff_result["different_settings"].append({
                    "key": key,
                    "value_a": policy_a[key],
                    "value_b": policy_b[key]
                })
        # A에만 있는 설정
        elif key in policy_a:
            diff_result["only_in_a"].append({
                "key": key,
                "value": policy_a[key]
            })
        # B에만 있는 설정
        else:
            diff_result["only_in_b"].append({
                "key": key,
                "value": policy_b[key]
            })
    
    return diff_result

def export_comparison_to_html(comparison: Dict[str, Any], output_path: str) -> bool:
    """
    비교 결과를 HTML 파일로 내보냅니다.
    
    Args:
        comparison: 비교 결과
        output_path: 출력 파일 경로
        
    Returns:
        성공 여부
    """
    try:
        # 비교 테이블 생성
        diff_table = generate_diff_table(comparison)
        
        # HTML 템플릿
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>정책 비교 결과</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .category {{ background-color: #f9f9f9; font-weight: bold; }}
                .significant {{ background-color: #ffe6e6; }}
                .positive {{ color: green; }}
                .negative {{ color: red; }}
                .policy-diff {{ margin-bottom: 10px; padding: 10px; border: 1px solid #ddd; }}
                .added {{ background-color: #e6ffe6; }}
                .removed {{ background-color: #ffe6e6; }}
                .modified {{ background-color: #e6f0ff; }}
            </style>
        </head>
        <body>
            <h1>정책 비교 결과</h1>
            <p>비교 시간: {comparison.get("timestamp", "")}</p>
            
            <h2>비교 대상</h2>
            <table>
                <tr>
                    <th></th>
                    <th>정책 세트</th>
                    <th>ID</th>
                </tr>
                <tr>
                    <td>정책 1</td>
                    <td>{comparison.get("metadata", {}).get("result1_policy_set", "")}</td>
                    <td>{comparison.get("metadata", {}).get("result1_id", 
(Content truncated due to size limit. Use line ranges to read in chunks)