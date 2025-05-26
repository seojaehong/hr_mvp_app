"""
정책 조합 시뮬레이션 및 시각화 모듈

이 모듈은 다양한 정책 조합에 대한 시뮬레이션을 실행하고 결과를 시각화하는 기능을 제공합니다.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Tuple
import logging
import json
from datetime import datetime
import itertools
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

def run_simulations_on_combinations(input_data: Dict[str, Any], policy_combinations: List[Dict[str, Any]], 
                                   max_workers: int = 4) -> Dict[str, Any]:
    """
    여러 정책 조합에 대해 시뮬레이션을 실행합니다.
    
    Args:
        input_data: 시뮬레이션 입력 데이터
        policy_combinations: 정책 조합 목록
        max_workers: 병렬 처리 작업자 수
        
    Returns:
        시뮬레이션 결과
    """
    from .policy_simulator import PolicySimulator
    
    # 결과 초기화
    simulation_results = {
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "input_data_id": input_data.get("id", "unknown"),
            "combinations_count": len(policy_combinations),
            "simulation_parameters": input_data.get("parameters", {})
        },
        "results": [],
        "metrics_summary": {},
        "best_combinations": {}
    }
    
    # 시뮬레이터 초기화
    simulator = PolicySimulator()
    
    # 병렬 처리로 시뮬레이션 실행
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_policy = {
            executor.submit(simulator.simulate, input_data, policy_set): policy_set
            for policy_set in policy_combinations
        }
        
        for future in as_completed(future_to_policy):
            policy_set = future_to_policy[future]
            try:
                result = future.result()
                # 결과 저장
                simulation_results["results"].append({
                    "policy_set": policy_set,
                    "result": result
                })
            except Exception as e:
                logger.error(f"정책 조합 {policy_set.get('name', 'unknown')} 시뮬레이션 중 오류 발생: {e}", exc_info=True)
                simulation_results["results"].append({
                    "policy_set": policy_set,
                    "error": str(e)
                })
    
    # 주요 지표 요약
    metrics = ["total_hours", "overtime_hours", "night_hours", "holiday_hours", 
               "base_pay", "overtime_pay", "night_pay", "holiday_pay", "total_pay"]
    
    metrics_data = {}
    for metric in metrics:
        values = []
        for result_item in simulation_results["results"]:
            if "result" in result_item and "time_summary" in result_item["result"]:
                values.append(result_item["result"]["time_summary"].get(metric, 0))
        
        if values:
            metrics_data[metric] = {
                "min": min(values),
                "max": max(values),
                "avg": sum(values) / len(values),
                "median": sorted(values)[len(values) // 2],
                "std": np.std(values)
            }
    
    simulation_results["metrics_summary"] = metrics_data
    
    # 최적 조합 찾기
    best_combinations = {}
    
    # 최소 총 근무시간
    if "total_hours" in metrics_data:
        min_total_hours = metrics_data["total_hours"]["min"]
        best_total_hours = []
        
        for result_item in simulation_results["results"]:
            if "result" in result_item and "time_summary" in result_item["result"]:
                if result_item["result"]["time_summary"].get("total_hours", 0) == min_total_hours:
                    best_total_hours.append({
                        "policy_set": result_item["policy_set"].get("name", "unknown"),
                        "total_hours": min_total_hours
                    })
        
        best_combinations["min_total_hours"] = best_total_hours
    
    # 최대 총 급여
    if "total_pay" in metrics_data:
        max_total_pay = metrics_data["total_pay"]["max"]
        best_total_pay = []
        
        for result_item in simulation_results["results"]:
            if "result" in result_item and "time_summary" in result_item["result"]:
                if result_item["result"]["time_summary"].get("total_pay", 0) == max_total_pay:
                    best_total_pay.append({
                        "policy_set": result_item["policy_set"].get("name", "unknown"),
                        "total_pay": max_total_pay
                    })
        
        best_combinations["max_total_pay"] = best_total_pay
    
    # 최적 비용 효율 (시간당 급여)
    best_efficiency = []
    max_efficiency = 0
    
    for result_item in simulation_results["results"]:
        if "result" in result_item and "time_summary" in result_item["result"]:
            total_hours = result_item["result"]["time_summary"].get("total_hours", 0)
            total_pay = result_item["result"]["time_summary"].get("total_pay", 0)
            
            if total_hours > 0:
                efficiency = total_pay / total_hours
                if not best_efficiency or efficiency > max_efficiency:
                    max_efficiency = efficiency
                    best_efficiency = [{
                        "policy_set": result_item["policy_set"].get("name", "unknown"),
                        "efficiency": efficiency,
                        "total_pay": total_pay,
                        "total_hours": total_hours
                    }]
                elif efficiency == max_efficiency:
                    best_efficiency.append({
                        "policy_set": result_item["policy_set"].get("name", "unknown"),
                        "efficiency": efficiency,
                        "total_pay": total_pay,
                        "total_hours": total_hours
                    })
    
    best_combinations["best_efficiency"] = best_efficiency
    
    simulation_results["best_combinations"] = best_combinations
    
    return simulation_results

def generate_heatmap(results_matrix: Dict[str, Any]) -> Dict[str, Any]:
    """
    시뮬레이션 결과를 히트맵 형태로 변환합니다.
    
    Args:
        results_matrix: 시뮬레이션 결과
        
    Returns:
        히트맵 데이터
    """
    # 히트맵 데이터 초기화
    heatmap_data = {
        "timestamp": datetime.now().isoformat(),
        "metadata": results_matrix.get("metadata", {}),
        "heatmaps": {}
    }
    
    # 결과 데이터 추출
    results = results_matrix.get("results", [])
    if not results:
        return heatmap_data
    
    # 정책 세트 이름 추출
    policy_sets = [result["policy_set"].get("name", f"정책 {i+1}") for i, result in enumerate(results)]
    
    # 주요 지표 추출
    metrics = ["total_hours", "overtime_hours", "night_hours", "holiday_hours", 
               "base_pay", "overtime_pay", "night_pay", "holiday_pay", "total_pay"]
    
    # 지표별 히트맵 데이터 생성
    for metric in metrics:
        # 지표 값 추출
        values = []
        for result in results:
            if "result" in result and "time_summary" in result["result"]:
                values.append(result["result"]["time_summary"].get(metric, 0))
            else:
                values.append(0)
        
        # 최소/최대값 계산
        min_value = min(values) if values else 0
        max_value = max(values) if values else 0
        
        # 정규화된 값 계산 (0~1 범위)
        normalized_values = []
        if max_value > min_value:
            normalized_values = [(v - min_value) / (max_value - min_value) for v in values]
        else:
            normalized_values = [0.5 for _ in values]
        
        # 히트맵 데이터 구성
        heatmap_data["heatmaps"][metric] = {
            "policy_sets": policy_sets,
            "values": values,
            "normalized_values": normalized_values,
            "min_value": min_value,
            "max_value": max_value
        }
    
    return heatmap_data

def generate_policy_combination_matrix(policy_options: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    정책 옵션들의 모든 가능한 조합을 생성합니다.
    
    Args:
        policy_options: 카테고리별 정책 옵션
        
    Returns:
        정책 조합 목록
    """
    # 결과 초기화
    combinations = []
    
    # 카테고리 및 옵션 추출
    categories = list(policy_options.keys())
    options_list = [policy_options[category] for category in categories]
    
    # 모든 가능한 조합 생성
    for combo in itertools.product(*options_list):
        # 조합 이름 생성
        combo_name = " + ".join([option.get("name", "unknown") for option in combo])
        
        # 정책 조합 구성
        policy_set = {
            "name": combo_name,
            "policies": list(combo),
            "categories": {categories[i]: combo[i].get("name", "unknown") for i in range(len(categories))}
        }
        
        combinations.append(policy_set)
    
    return combinations

def filter_valid_combinations(combinations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    유효한 정책 조합만 필터링합니다.
    
    Args:
        combinations: 모든 정책 조합 목록
        
    Returns:
        유효한 정책 조합 목록
    """
    valid_combinations = []
    
    for combo in combinations:
        policies = combo.get("policies", [])
        
        # 충돌 확인
        has_conflict = False
        for i, policy1 in enumerate(policies):
            conflicts_with = policy1.get("conflicts_with", [])
            for j, policy2 in enumerate(policies):
                if i != j and policy2.get("name", "") in conflicts_with:
                    has_conflict = True
                    break
            
            if has_conflict:
                break
        
        # 충돌이 없는 경우만 추가
        if not has_conflict:
            valid_combinations.append(combo)
    
    return valid_combinations

def export_simulation_results_to_html(simulation_results: Dict[str, Any], output_path: str) -> bool:
    """
    시뮬레이션 결과를 HTML 파일로 내보냅니다.
    
    Args:
        simulation_results: 시뮬레이션 결과
        output_path: 출력 파일 경로
        
    Returns:
        성공 여부
    """
    try:
        # 결과 데이터 추출
        results = simulation_results.get("results", [])
        metrics_summary = simulation_results.get("metrics_summary", {})
        best_combinations = simulation_results.get("best_combinations", {})
        
        # 결과 테이블 데이터 구성
        table_data = []
        for result_item in results:
            policy_set = result_item.get("policy_set", {})
            result = result_item.get("result", {})
            
            if "time_summary" in result:
                time_summary = result["time_summary"]
                
                row = {
                    "정책 세트": policy_set.get("name", "unknown"),
                    "총 근무시간": time_summary.get("total_hours", 0),
                    "연장 근무시간": time_summary.get("overtime_hours", 0),
                    "야간 근무시간": time_summary.get("night_hours", 0),
                    "휴일 근무시간": time_summary.get("holiday_hours", 0),
                    "기본급": f"{time_summary.get('base_pay', 0):,}원",
                    "연장근로수당": f"{time_summary.get('overtime_pay', 0):,}원",
                    "야간근로수당": f"{time_summary.get('night_pay', 0):,}원",
                    "휴일근로수당": f"{time_summary.get('holiday_pay', 0):,}원",
                    "총 지급액": f"{time_summary.get('total_pay', 0):,}원"
                }
                
                table_data.append(row)
        
        # 결과 테이블 생성
        if table_data:
            results_df = pd.DataFrame(table_data)
        else:
            results_df = pd.DataFrame(columns=["정책 세트", "총 근무시간", "연장 근무시간", "야간 근무시간", "휴일 근무시간",
                                              "기본급", "연장근로수당", "야간근로수당", "휴일근로수당", "총 지급액"])
        
        # 지표 요약 테이블 데이터 구성
        summary_data = []
        for metric, values in metrics_summary.items():
            # 지표명 한글화
            metric_name = {
                "total_hours": "총 근무시간",
                "overtime_hours": "연장 근무시간",
                "night_hours": "야간 근무시간",
                "holiday_hours": "휴일 근무시간",
                "base_pay": "기본급",
                "overtime_pay": "연장근로수당",
                "night_pay": "야간근로수당",
                "holiday_pay": "휴일근로수당",
                "total_pay": "총 지급액"
            }.get(metric, metric)
            
            # 단위 추가
            unit = "원" if "pay" in metric else "시간"
            
            # 값 포맷팅
            min_value = f"{values.get('min', 0):,} {unit}"
            max_value = f"{values.get('max', 0):,} {unit}"
            avg_value = f"{values.get('avg', 0):.2f} {unit}"
            median_value = f"{values.get('median', 0):,} {unit}"
            std_value = f"{values.get('std', 0):.2f} {unit}"
            
            summary_data.append({
                "지표": metric_name,
                "최소값": min_value,
                "최대값": max_value,
                "평균": avg_value,
                "중앙값": median_value,
                "표준편차": std_value
            })
        
        # 지표 요약 테이블 생성
        if summary_data:
            summary_df = pd.DataFrame(summary_data)
        else:
            summary_df = pd.DataFrame(columns=["지표", "최소값", "최대값", "평균", "중앙값", "표준편차"])
        
        # HTML 템플릿
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>정책 시뮬레이션 결과</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2, h3 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .highlight {{ background-color: #e6f7ff; }}
                .best {{ background-color: #e6ffe6; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>정책 시뮬레이션 결과</h1>
            <p>시뮬레이션 시간: {simulation_results.get("timestamp", "")}</p>
            
            <h2>최적 정책 조합</h2>
        """
        
        # 최소 총 근무시간 정책
        if "min_total_hours" in best_combinations:
            html_content += "<h3>최소 총 근무시간</h3>"
            html_content += "<ul>"
            for combo in best_combinations["min_total_hours"]:
                html_content += f"<li><strong>{combo.get('policy_set', '')}</strong>: {combo.get('total_hours', 0)} 시간</li>"
            html_content += "</ul>"
        
        # 최대 총 급여 정책
        if "max_total_pay" in best_combinations:
            html_content += "<h3>최대 총 급여</h3>"
            html_content += "<ul>"
            for combo in best_combinations["max_total_pay"]:
                html_content += f"<li><strong>{combo.get('policy_set', '')}</strong>: {combo.get('total_pay', 0):,} 원</li>"
            html_content += "</ul>"
        
        # 최적 비용 효율 정책
        if "best_efficiency" in best_combinations:
            html_content += "<h3>최적 비용 효율 (시간당 급여)</h3>"
            html_content += "<ul>"
            for combo in best_combinations["best_efficiency"]:
                html_content += f"<li><strong>{combo.get('policy_set', '')}</strong>: {combo.get('efficiency', 0):,.2f} 원/시간 (총 급여: {combo.get('total_pay', 0):,} 원, 총 시간: {combo.get('total_hours', 0)} 시간)</li>"
            html_content += "</ul>"
        
        # 지표 요약 테이블
        html_content += f"""
            <h2>지표 요약</h2>
            {summary_df.to_html(index=False)}
            
            <h2>모든 시뮬레이션 결과</h2>
            {results_df.to_html(index=False)}
        </body>
        </html>
        """
        
        # HTML 파일 저장
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"시뮬레이션 결과가 {output_path}에 저장되었습니다.")
        return True
    
    except Exception as e:
        logger.error(f"시뮬레이션 결과 생성 중 오류 발생: {e}", exc_info=True)
        return False

def export_simulation_results_to_json(simulation_results: Dict[str, Any], output_path: str) -> bool:
    """
    시뮬레이션 결과를 JSON 파일로 내보냅니다.
    
    Args:
        simulation_results: 시뮬레이션 결과
        output_path: 출력 파일 경로
        
    Returns:
        성공 여부
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(simulation_results, f, ensure_ascii=False, indent=2) # 수정된 부분
        logger.info(f"시뮬레이션 결과가 {output_path}에 저장되었습니다.")
        return True
    except Exception as e:
        logger.error(f"시뮬레이션 결과 저장 중 오류 발생: {e}", exc_info=True)
        return False

# 여기에 파일의 끝이어야 합니다.
# 만약 이 함수 정의 이후에 다른 코드(주석 제외)나 불필요한 문자(예: 닫는 중괄호 '}')가 있다면
# SyntaxError: unexpected EOF while parsing 오류가 발생할 수 있습니다.