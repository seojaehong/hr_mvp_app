"""
정책 요약 및 시각화 모듈

이 모듈은 정책 기반 계산 결과를 요약하고 시각화하는 기능을 제공합니다.
"""

import json
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def summarize_trace(trace: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    계산 과정 추적 로그를 요약합니다.
    
    Args:
        trace: 계산 과정 추적 로그 리스트
        
    Returns:
        요약된 추적 정보
    """
    if not trace:
        return {"summary": "추적 정보 없음", "steps": 0, "decisions": []}
    
    # 단계 수 계산
    steps = len(trace)
    
    # 주요 결정 사항 추출
    decisions = []
    for step in trace:
        if step.get("type") == "decision" or step.get("importance", 0) >= 3:
            decisions.append({
                "step": step.get("step", "unknown"),
                "description": step.get("description", ""),
                "policy": step.get("policy", ""),
                "result": step.get("result", "")
            })
    
    # 정책별 영향도 분석
    policy_impacts = {}
    for step in trace:
        policy = step.get("policy")
        if policy:
            if policy not in policy_impacts:
                policy_impacts[policy] = {
                    "count": 0,
                    "importance_sum": 0,
                    "key_decisions": 0
                }
            
            policy_impacts[policy]["count"] += 1
            policy_impacts[policy]["importance_sum"] += step.get("importance", 1)
            
            if step.get("importance", 0) >= 4:
                policy_impacts[policy]["key_decisions"] += 1
    
    # 정책 영향도 순위화
    ranked_policies = sorted(
        policy_impacts.items(),
        key=lambda x: (x[1]["key_decisions"], x[1]["importance_sum"]),
        reverse=True
    )
    
    # 요약 정보 구성
    summary = {
        "summary": f"{steps}단계 계산 과정, {len(decisions)}개 주요 결정 포함",
        "steps": steps,
        "decisions": decisions,
        "policy_impacts": [
            {
                "policy": policy,
                "impact_score": data["importance_sum"] / data["count"] if data["count"] > 0 else 0,
                "key_decisions": data["key_decisions"],
                "usage_count": data["count"]
            }
            for policy, data in ranked_policies
        ]
    }
    
    return summary

def generate_policy_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    계산 결과에 적용된 정책을 요약합니다.
    
    Args:
        result: 계산 결과 데이터
        
    Returns:
        정책 요약 정보
    """
    # 기본 정보 초기화
    summary = {
        "timestamp": datetime.now().isoformat(),
        "applied_policies": [],
        "policy_categories": {},
        "key_metrics": {},
        "compliance_alerts": []
    }
    
    # 적용된 정책 정보 추출
    applied_policies = result.get("applied_policies", [])
    if not applied_policies and "metadata" in result:
        applied_policies = result.get("metadata", {}).get("applied_policies", [])
    
    # 정책 카테고리별 분류
    for policy in applied_policies:
        policy_name = policy.get("name", "")
        policy_category = policy.get("category", "기타")
        
        policy_info = {
            "name": policy_name,
            "description": policy.get("description", ""),
            "version": policy.get("version", ""),
            "enabled": policy.get("enabled", True),
            "source": policy.get("source", "default")
        }
        
        summary["applied_policies"].append(policy_info)
        
        if policy_category not in summary["policy_categories"]:
            summary["policy_categories"][policy_category] = []
        
        summary["policy_categories"][policy_category].append(policy_name)
    
    # 주요 지표 추출
    time_summary = result.get("time_summary", {})
    if time_summary:
        summary["key_metrics"] = {
            "total_work_days": time_summary.get("work_days", 0),
            "total_work_hours": time_summary.get("total_hours", 0),
            "regular_hours": time_summary.get("regular_hours", 0),
            "overtime_hours": time_summary.get("overtime_hours", 0),
            "night_hours": time_summary.get("night_hours", 0),
            "holiday_hours": time_summary.get("holiday_hours", 0),
            "base_pay": time_summary.get("base_pay", 0),
            "overtime_pay": time_summary.get("overtime_pay", 0),
            "night_pay": time_summary.get("night_pay", 0),
            "holiday_pay": time_summary.get("holiday_pay", 0),
            "total_pay": time_summary.get("total_pay", 0)
        }
    
    # 컴플라이언스 알림 추출
    compliance_alerts = result.get("compliance_alerts", [])
    if not compliance_alerts and "metadata" in result:
        compliance_alerts = result.get("metadata", {}).get("compliance_alerts", [])
    
    summary["compliance_alerts"] = compliance_alerts
    
    # 추적 정보 요약 추가
    trace = result.get("trace", [])
    if trace:
        summary["trace_summary"] = summarize_trace(trace)
    
    return summary

def render_policy_table(policies: Dict[str, Any]) -> pd.DataFrame:
    """
    정책 정보를 테이블 형태로 변환합니다.
    
    Args:
        policies: 정책 정보 딕셔너리
        
    Returns:
        정책 정보 테이블
    """
    # 정책 정보 추출
    policy_data = []
    
    for policy in policies.get("applied_policies", []):
        policy_data.append({
            "정책명": policy.get("name", ""),
            "설명": policy.get("description", ""),
            "버전": policy.get("version", ""),
            "활성화": "예" if policy.get("enabled", True) else "아니오",
            "출처": policy.get("source", "default")
        })
    
    # 데이터프레임 생성
    if policy_data:
        return pd.DataFrame(policy_data)
    else:
        return pd.DataFrame(columns=["정책명", "설명", "버전", "활성화", "출처"])

def render_metrics_table(metrics: Dict[str, Any]) -> pd.DataFrame:
    """
    주요 지표를 테이블 형태로 변환합니다.
    
    Args:
        metrics: 주요 지표 딕셔너리
        
    Returns:
        주요 지표 테이블
    """
    # 지표 데이터 추출
    metrics_data = []
    
    for key, value in metrics.items():
        # 지표명 한글화
        metric_name = {
            "total_work_days": "총 근무일수",
            "total_work_hours": "총 근무시간",
            "regular_hours": "정규 근무시간",
            "overtime_hours": "연장 근무시간",
            "night_hours": "야간 근무시간",
            "holiday_hours": "휴일 근무시간",
            "base_pay": "기본급",
            "overtime_pay": "연장근로수당",
            "night_pay": "야간근로수당",
            "holiday_pay": "휴일근로수당",
            "total_pay": "총 지급액"
        }.get(key, key)
        
        # 단위 추가
        unit = "원" if "pay" in key else "시간" if "hours" in key else "일" if "days" in key else ""
        
        # 값 포맷팅
        formatted_value = f"{value:,}" if isinstance(value, (int, float)) else str(value)
        if unit:
            formatted_value = f"{formatted_value} {unit}"
        
        metrics_data.append({
            "지표": metric_name,
            "값": formatted_value
        })
    
    # 데이터프레임 생성
    if metrics_data:
        return pd.DataFrame(metrics_data)
    else:
        return pd.DataFrame(columns=["지표", "값"])

def render_alerts_table(alerts: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    컴플라이언스 알림을 테이블 형태로 변환합니다.
    
    Args:
        alerts: 컴플라이언스 알림 리스트
        
    Returns:
        컴플라이언스 알림 테이블
    """
    # 알림 데이터 추출
    alerts_data = []
    
    for alert in alerts:
        alerts_data.append({
            "유형": alert.get("type", ""),
            "심각도": alert.get("severity", ""),
            "메시지": alert.get("message", ""),
            "관련 정책": alert.get("related_policy", "")
        })
    
    # 데이터프레임 생성
    if alerts_data:
        return pd.DataFrame(alerts_data)
    else:
        return pd.DataFrame(columns=["유형", "심각도", "메시지", "관련 정책"])

def generate_policy_impact_chart_data(trace_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    정책 영향도 차트 데이터를 생성합니다.
    
    Args:
        trace_summary: 추적 정보 요약
        
    Returns:
        차트 데이터
    """
    policy_impacts = trace_summary.get("policy_impacts", [])
    
    # 차트 데이터 구성
    chart_data = {
        "labels": [],
        "impact_scores": [],
        "key_decisions": [],
        "usage_counts": []
    }
    
    for impact in policy_impacts:
        chart_data["labels"].append(impact.get("policy", ""))
        chart_data["impact_scores"].append(impact.get("impact_score", 0))
        chart_data["key_decisions"].append(impact.get("key_decisions", 0))
        chart_data["usage_counts"].append(impact.get("usage_count", 0))
    
    return chart_data

def export_policy_summary_to_html(summary: Dict[str, Any], output_path: str) -> bool:
    """
    정책 요약 정보를 HTML 파일로 내보냅니다.
    
    Args:
        summary: 정책 요약 정보
        output_path: 출력 파일 경로
        
    Returns:
        성공 여부
    """
    try:
        # 정책 테이블
        policy_df = render_policy_table(summary)
        
        # 지표 테이블
        metrics_df = render_metrics_table(summary.get("key_metrics", {}))
        
        # 알림 테이블
        alerts_df = render_alerts_table(summary.get("compliance_alerts", []))
        
        # HTML 템플릿
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>정책 요약 보고서</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .category {{ background-color: #f9f9f9; font-weight: bold; }}
                .alert-high {{ color: red; }}
                .alert-medium {{ color: orange; }}
                .alert-low {{ color: blue; }}
            </style>
        </head>
        <body>
            <h1>정책 요약 보고서</h1>
            <p>생성 시간: {summary.get("timestamp", "")}</p>
            
            <h2>적용된 정책</h2>
            {policy_df.to_html(index=False)}
            
            <h2>정책 카테고리</h2>
            <table>
                <tr>
                    <th>카테고리</th>
                    <th>정책</th>
                </tr>
        """
        
        # 카테고리별 정책 추가
        for category, policies in summary.get("policy_categories", {}).items():
            html_content += f"""
                <tr>
                    <td class="category">{category}</td>
                    <td>{", ".join(policies)}</td>
                </tr>
            """
        
        html_content += f"""
            </table>
            
            <h2>주요 지표</h2>
            {metrics_df.to_html(index=False)}
            
            <h2>컴플라이언스 알림</h2>
            {alerts_df.to_html(index=False)}
        """
        
        # 추적 정보 요약 추가
        if "trace_summary" in summary:
            trace_summary = summary["trace_summary"]
            html_content += f"""
            <h2>계산 과정 요약</h2>
            <p>{trace_summary.get("summary", "")}</p>
            
            <h3>주요 결정 사항</h3>
            <table>
                <tr>
                    <th>단계</th>
                    <th>설명</th>
                    <th>정책</th>
                    <th>결과</th>
                </tr>
            """
            
            # 주요 결정 사항 추가
            for decision in trace_summary.get("decisions", []):
                html_content += f"""
                <tr>
                    <td>{decision.get("step", "")}</td>
                    <td>{decision.get("description", "")}</td>
                    <td>{decision.get("policy", "")}</td>
                    <td>{decision.get("result", "")}</td>
                </tr>
                """
            
            html_content += """
            </table>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # HTML 파일 저장
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"정책 요약 보고서가 {output_path}에 저장되었습니다.")
        return True
    
    except Exception as e:
        logger.error(f"정책 요약 보고서 생성 중 오류 발생: {e}", exc_info=True)
        return False

def export_policy_summary_to_json(summary: Dict[str, Any], output_path: str) -> bool:
    """
    정책 요약 정보를 JSON 파일로 내보냅니다.
    
    Args:
        summary: 정책 요약 정보
        output_path: 출력 파일 경로
        
    Returns:
        성공 여부
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        logger.info(f"정책 요약 정보가 {output_path}에 저장되었습니다.")
        return True
    
    except Exception as e:
        logger.error(f"정책 요약 정보 저장 중 오류 발생: {e}", exc_info=True)
        return False
