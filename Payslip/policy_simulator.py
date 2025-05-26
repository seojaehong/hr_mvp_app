"""
다중 정책 시나리오 실행기

동일한 입력 데이터에 여러 정책 조합을 적용하고 결과를 비교하는 시뮬레이션 엔진입니다.
"""

import os
import yaml
import json
import copy
from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal
import datetime

from Payslip.Worktime.schema import  (
    TimeCardInputData, TimeCardRecord, WorkTimeCalculationResult,
    TimeSummary, WorkDayDetail, ErrorDetails, ComplianceAlert
)
from Payslip.policy_manager import PolicyManager
from Payslip.timecard_calculator import TimeCardBasedCalculator # "_refactored" 부분을 삭제!

class PolicySimulator:
    """
    정책 시뮬레이터 클래스
    
    여러 정책 조합을 동일한 입력 데이터에 적용하고 결과를 비교하는 시뮬레이션 엔진입니다.
    """
    
    def __init__(self):
        """
        정책 시뮬레이터 초기화
        """
        self.base_policy_manager = PolicyManager()
        self.results_cache = {}
    
    def simulate_across_policies(
        self, 
        input_data: TimeCardInputData, 
        policy_sets: List[Dict[str, Any]],
        policy_set_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        여러 정책 조합에 대해 시뮬레이션 실행
        
        Args:
            input_data: 타임카드 입력 데이터
            policy_sets: 정책 조합 목록 (각 정책 조합은 정책 키-값 쌍의 딕셔너리)
            policy_set_names: 정책 조합 이름 목록 (제공되지 않으면 자동 생성)
            
        Returns:
            시뮬레이션 결과 딕셔너리
        """
        results = {}
        
        # 정책 조합 이름이 제공되지 않은 경우 자동 생성
        if policy_set_names is None:
            policy_set_names = [f"정책조합_{i+1}" for i in range(len(policy_sets))]
        
        # 각 정책 조합에 대해 시뮬레이션 실행
        for i, (policy_set, policy_name) in enumerate(zip(policy_sets, policy_set_names)):
            # 정책 관리자 생성 및 정책 설정
            policy_manager = copy.deepcopy(self.base_policy_manager)
            for key, value in policy_set.items():
                policy_manager.set(key, value)
            
            # 계산기 생성 및 계산 실행
            calculator = TimeCardBasedCalculator(policy_manager=policy_manager)
            result = calculator.calculate(input_data)
            
            # 결과 저장
            results[policy_name] = {
                "result": result,
                "policy_set": policy_set,
                "timestamp": datetime.datetime.now().isoformat()
            }
        
        # 결과 캐시에 저장
        cache_key = f"{input_data.employee_id}_{input_data.period}"
        self.results_cache[cache_key] = results
        
        return results
    
    def compare_results(
        self, 
        result_a: Union[WorkTimeCalculationResult, str], 
        result_b: Union[WorkTimeCalculationResult, str],
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        두 계산 결과 비교
        
        Args:
            result_a: 첫 번째 계산 결과 또는 결과 이름
            result_b: 두 번째 계산 결과 또는 결과 이름
            detailed: 상세 비교 여부
            
        Returns:
            비교 결과 딕셔너리
        """
        # 결과 이름이 제공된 경우 캐시에서 결과 가져오기
        if isinstance(result_a, str) and isinstance(result_b, str):
            for cache_key, cached_results in self.results_cache.items():
                if result_a in cached_results and result_b in cached_results:
                    result_a = cached_results[result_a]["result"]
                    result_b = cached_results[result_b]["result"]
                    break
        
        # 결과 객체가 아닌 경우 오류
        if not isinstance(result_a, WorkTimeCalculationResult) or not isinstance(result_b, WorkTimeCalculationResult):
            raise ValueError("Invalid result objects for comparison")
        
        # 기본 비교 결과
        comparison = {
            "time_summary_diff": self._compare_time_summary(result_a.time_summary, result_b.time_summary),
            "warnings_diff": self._compare_warnings(result_a.warnings, result_b.warnings),
            "compliance_alerts_diff": self._compare_compliance_alerts(result_a.compliance_alerts, result_b.compliance_alerts),
            "processing_mode_diff": result_a.processing_mode != result_b.processing_mode,
            "error_diff": self._compare_errors(result_a.error, result_b.error)
        }
        
        # 상세 비교 결과
        if detailed:
            comparison["daily_details_diff"] = self._compare_daily_details(result_a.daily_details, result_b.daily_details)
            comparison["trace_diff"] = self._compare_traces(result_a.trace, result_b.trace)
        
        # 차이점 요약
        comparison["summary"] = self._summarize_differences(comparison)
        
        return comparison
    
    def _compare_time_summary(self, summary_a: TimeSummary, summary_b: TimeSummary) -> Dict[str, Any]:
        """
        두 시간 요약 비교
        
        Args:
            summary_a: 첫 번째 시간 요약
            summary_b: 두 번째 시간 요약
            
        Returns:
            비교 결과 딕셔너리
        """
        diff = {}
        
        # 각 필드 비교
        for field in [
            "regular_hours", "overtime_hours", "night_hours", 
            "holiday_hours", "holiday_overtime_hours", "total_net_work_hours"
        ]:
            value_a = getattr(summary_a, field)
            value_b = getattr(summary_b, field)
            
            if value_a != value_b:
                diff[field] = {
                    "a": float(value_a),
                    "b": float(value_b),
                    "diff": float(value_b - value_a),
                    "percent_change": float((value_b - value_a) / value_a * 100) if value_a != 0 else float('inf')
                }
        
        return diff
    
    def _compare_warnings(self, warnings_a: List[str], warnings_b: List[str]) -> Dict[str, Any]:
        """
        두 경고 목록 비교
        
        Args:
            warnings_a: 첫 번째 경고 목록
            warnings_b: 두 번째 경고 목록
            
        Returns:
            비교 결과 딕셔너리
        """
        return {
            "only_in_a": list(set(warnings_a) - set(warnings_b)),
            "only_in_b": list(set(warnings_b) - set(warnings_a)),
            "common": list(set(warnings_a) & set(warnings_b))
        }
    
    def _compare_compliance_alerts(self, alerts_a: List[ComplianceAlert], alerts_b: List[ComplianceAlert]) -> Dict[str, Any]:
        """
        두 컴플라이언스 알림 목록 비교
        
        Args:
            alerts_a: 첫 번째 컴플라이언스 알림 목록
            alerts_b: 두 번째 컴플라이언스 알림 목록
            
        Returns:
            비교 결과 딕셔너리
        """
        # 알림 코드 추출
        codes_a = [alert.alert_code for alert in alerts_a]
        codes_b = [alert.alert_code for alert in alerts_b]
        
        # 심각도 비교
        severity_diff = {}
        common_codes = set(codes_a) & set(codes_b)
        
        for code in common_codes:
            alert_a = next(alert for alert in alerts_a if alert.alert_code == code)
            alert_b = next(alert for alert in alerts_b if alert.alert_code == code)
            
            if alert_a.severity != alert_b.severity:
                severity_diff[code] = {
                    "a": alert_a.severity,
                    "b": alert_b.severity
                }
        
        return {
            "only_in_a": list(set(codes_a) - set(codes_b)),
            "only_in_b": list(set(codes_b) - set(codes_a)),
            "common": list(common_codes),
            "severity_diff": severity_diff
        }
    
    def _compare_errors(self, error_a: Optional[ErrorDetails], error_b: Optional[ErrorDetails]) -> Dict[str, Any]:
        """
        두 오류 비교
        
        Args:
            error_a: 첫 번째 오류
            error_b: 두 번째 오류
            
        Returns:
            비교 결과 딕셔너리
        """
        if error_a is None and error_b is None:
            return {"has_diff": False}
        
        if error_a is None:
            return {
                "has_diff": True,
                "only_in_b": {
                    "error_code": error_b.error_code,
                    "message": error_b.message
                }
            }
        
        if error_b is None:
            return {
                "has_diff": True,
                "only_in_a": {
                    "error_code": error_a.error_code,
                    "message": error_a.message
                }
            }
        
        return {
            "has_diff": error_a.error_code != error_b.error_code or error_a.message != error_b.message,
            "a": {
                "error_code": error_a.error_code,
                "message": error_a.message
            },
            "b": {
                "error_code": error_b.error_code,
                "message": error_b.message
            }
        }
    
    def _compare_daily_details(self, details_a: Dict[str, WorkDayDetail], details_b: Dict[str, WorkDayDetail]) -> Dict[str, Any]:
        """
        두 일일 상세 정보 비교
        
        Args:
            details_a: 첫 번째 일일 상세 정보
            details_b: 두 번째 일일 상세 정보
            
        Returns:
            비교 결과 딕셔너리
        """
        diff = {}
        
        # 날짜 집합
        dates_a = set(details_a.keys())
        dates_b = set(details_b.keys())
        
        # 날짜 비교
        diff["only_in_a"] = list(dates_a - dates_b)
        diff["only_in_b"] = list(dates_b - dates_a)
        
        # 공통 날짜에 대한 상세 비교
        common_dates = dates_a & dates_b
        daily_diffs = {}
        
        for date in common_dates:
            day_a = details_a[date]
            day_b = details_b[date]
            
            day_diff = {}
            for field in ["regular_hours", "overtime_hours", "night_hours", "holiday_hours", "holiday_overtime_hours"]:
                value_a = getattr(day_a, field)
                value_b = getattr(day_b, field)
                
                if value_a != value_b:
                    day_diff[field] = {
                        "a": float(value_a),
                        "b": float(value_b),
                        "diff": float(value_b - value_a)
                    }
            
            if day_diff:
                daily_diffs[date] = day_diff
        
        diff["daily_diffs"] = daily_diffs
        
        return diff
    
    def _compare_traces(self, trace_a: List[Dict[str, Any]], trace_b: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        두 추적 로그 비교
        
        Args:
            trace_a: 첫 번째 추적 로그
            trace_b: 두 번째 추적 로그
            
        Returns:
            비교 결과 딕셔너리
        """
        # 추적 로그 유형 추출
        types_a = [entry.get("type") for entry in trace_a if "type" in entry]
        types_b = [entry.get("type") for entry in trace_b if "type" in entry]
        
        # 정책 적용 추적 로그 추출
        policy_traces_a = [entry for entry in trace_a if entry.get("type") == "policy_applied"]
        policy_traces_b = [entry for entry in trace_b if entry.get("type") == "policy_applied"]
        
        # 정책 키 추출
        policy_keys_a = [entry.get("policy_key") for entry in policy_traces_a if "policy_key" in entry]
        policy_keys_b = [entry.get("policy_key") for entry in policy_traces_b if "policy_key" in entry]
        
        return {
            "trace_types": {
                "only_in_a": list(set(types_a) - set(types_b)),
                "only_in_b": list(set(types_b) - set(types_a)),
                "common": list(set(types_a) & set(types_b))
            },
            "policy_keys": {
                "only_in_a": list(set(policy_keys_a) - set(policy_keys_b)),
                "only_in_b": list(set(policy_keys_b) - set(policy_keys_a)),
                "common": list(set(policy_keys_a) & set(policy_keys_b))
            },
            "trace_count": {
                "a": len(trace_a),
                "b": len(trace_b),
                "diff": len(trace_b) - len(trace_a)
            }
        }
    
    def _summarize_differences(self, comparison: Dict[str, Any]) -> Dict[str, Any]:
        """
        비교 결과 요약
        
        Args:
            comparison: 비교 결과 딕셔너리
            
        Returns:
            요약 딕셔너리
        """
        summary = {
            "has_differences": False,
            "significant_differences": [],
            "minor_differences": []
        }
        
        # 시간 요약 차이 확인
        time_summary_diff = comparison.get("time_summary_diff", {})
        if time_summary_diff:
            summary["has_differences"] = True
            
            for field, diff in time_summary_diff.items():
                if abs(diff["percent_change"]) > 5:  # 5% 이상 차이나면 중요한 차이로 간주
                    summary["significant_differences"].append({
                        "field": field,
                        "diff": diff["diff"],
                        "percent_change": diff["percent_change"]
                    })
                else:
                    summary["minor_differences"].append({
                        "field": field,
                        "diff": diff["diff"],
                        "percent_change": diff["percent_change"]
                    })
        
        # 경고 차이 확인
        warnings_diff = comparison.get("warnings_diff", {})
        if warnings_diff.get("only_in_a") or warnings_diff.get("only_in_b"):
            summary["has_differences"] = True
            
            if len(warnings_diff.get("only_in_a", [])) > 0:
                summary["minor_differences"].append({
                    "field": "warnings",
                    "only_in_a_count": len(warnings_diff["only_in_a"])
                })
            
            if len(warnings_diff.get("only_in_b", [])) > 0:
                summary["minor_differences"].append({
                    "field": "warnings",
                    "only_in_b_count": len(warnings_diff["only_in_b"])
                })
        
        # 컴플라이언스 알림 차이 확인
        compliance_alerts_diff = comparison.get("compliance_alerts_diff", {})
        if (compliance_alerts_diff.get("only_in_a") or 
            compliance_alerts_diff.get("only_in_b") or 
            compliance_alerts_diff.get("severity_diff")):
            summary["has_differences"] = True
            
            if len(compliance_alerts_diff.get("only_in_a", [])) > 0:
                summary["significant_differences"].append({
                    "field": "compliance_alerts",
                    "only_in_a_count": len(compliance_alerts_diff["only_in_a"])
                })
            
            if len(compliance_alerts_diff.get("only_in_b", [])) > 0:
                summary["significant_differences"].append({
                    "field": "compliance_alerts",
                    "only_in_b_count": len(compliance_alerts_diff["only_in_b"])
                })
            
            if compliance_alerts_diff.get("severity_diff"):
                summary["significant_differences"].append({
                    "field": "compliance_alerts_severity",
                    "diff_count": len(compliance_alerts_diff["severity_diff"])
                })
        
        # 처리 모드 차이 확인
        if comparison.get("processing_mode_diff"):
            summary["has_differences"] = True
            summary["significant_differences"].append({
                "field": "processing_mode",
                "diff": True
            })
        
        # 오류 차이 확인
        error_diff = comparison.get("error_diff", {})
        if error_diff.get("has_diff"):
            summary["has_differences"] = True
            summary["significant_differences"].append({
                "field": "error",
                "diff": True
            })
        
        return summary
    
    def summarize_policy_trace(self, result: WorkTimeCalculationResult) -> Dict[str, Any]:
        """
        정책 추적 로그 요약
        
        Args:
            result: 계산 결과
            
        Returns:
            추적 로그 요약 딕셔너리
        """
        summary = {
            "applied_policies": {},
            "policy_impact": {},
            "calculation_flow": [],
            "warnings": result.warnings,
            "compliance_alerts": [
                {
                    "alert_code": alert.alert_code,
                    "message": alert.message,
                    "severity": alert.severity
                }
                for alert in result.compliance_alerts
            ]
        }
        
        # 추적 로그 분석
        for entry in result.trace:
            entry_type = entry.get("type")
            
            if entry_type == "policy_applied":
                policy_key = entry.get("policy_key")
                policy_value = entry.get("policy_value")
                
                if policy_key:
                    summary["applied_policies"][policy_key] = policy_value
                    
                    # 정책 영향 추적
                    if "impact" in entry:
                        summary["policy_impact"][policy_key] = entry["impact"]
            
            # 계산 흐름 추적
            if entry_type in ["calculation_step", "policy_applied", "validation", "warning"]:
                summary["calculation_flow"].append({
                    "type": entry_type,
                    "message": entry.get("message", ""),
                    "timestamp": entry.get("timestamp", "")
                })
        
        return summary
    
    def save_simulation_results(self, results: Dict[str, Any], output_path: str) -> str:
        """
        시뮬레이션 결과 저장
        
        Args:
            results: 시뮬레이션 결과 딕셔너리
            output_path: 출력 파일 경로
            
        Returns:
            저장된 파일 경로
        """
        # 결과 직렬화
        serialized_results = {}
        
        for policy_name, result_data in results.items():
            result = result_data["result"]
            
            # WorkTimeCalculationResult 객체 직렬화
            serialized_result = {
                "processing_mode": result.processing_mode,
                "time_summary": {
                    "regular_hours": float(result.time_summary.regular_hours),
                    "overtime_hours": float(result.time_summary.overtime_hours),
                    "night_hours": float(result.time_summary.night_hours),
                    "holiday_hours": float(result.time_summary.holiday_hours),
                    "holiday_overtime_hours": float(result.time_summary.holiday_overtime_hours),
                    "total_net_work_hours": float(result.time_summary.total_net_work_hours)
                },
                "warnings": result.warnings,
                "compliance_alerts": [
                    {
                        "alert_code": alert.alert_code,
                        "message": alert.message,
                        "severity": alert.severity
                    }
                    for alert in result.compliance_alerts
                ],
                "trace": result.trace
            }
            
            # 오류가 있는 경우 추가
            if result.error:
                serialized_result["error"] = {
                    "error_code": result.error.error_code,
                    "message": result.error.message
                }
            
            # 일일 상세 정보 직렬화
            serialized_result["daily_details"] = {}
            for date, detail in result.daily_details.items():
                serialized_result["daily_details"][date] = {
                    "regular_hours": float(detail.regular_hours),
                    "overtime_hours": float(detail.overtime_hours),
                    "night_hours": float(detail.night_hours),
                    "holiday_hours": float(detail.holiday_hours),
                    "holiday_overtime_hours": float(detail.holiday_overtime_hours)
                }
            
            # 결과 데이터 저장
            serialized_results[policy_name] = {
                "result": serialized_result,
                "policy_set": result_data["policy_set"],
                "timestamp": result_data["timestamp"]
            }
        
        # JSON 파일로 저장
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(serialized_results, f, ensure_ascii=False, indent=2)
        
        return output_path
    
    def load_simulation_results(self, input_path: str) -> Dict[str, Any]:
        """
        시뮬레이션 결과 로드
        
        Args:
            input_path: 입력 파일 경로
            
        Returns:
            시뮬레이션 결과 딕셔너리
        """
        # JSON 파일에서 로드
        with open(input_path, 'r', encoding='utf-8') as f:
            serialized_results = json.load(f)
        
        # 결과 역직렬화
        results = {}
        
        for policy_name, result_data in serialized_results.items():
            serialized_result = result_data["result"]
            
            # TimeSummary 객체 생성
            time_summary = TimeSummary(
                regular_hours=Decimal(str(serialized_result["time_summary"]["regular_hours"])),
                overtime_hours=Decimal(str(serialized_result["time_summary"]["overtime_hours"])),
                night_hours=Decimal(str(serialized_result["time_summary"]["night_hours"])),
                holiday_hours=Decimal(str(serialized_result["time_summary"]["holiday_hours"])),
                holiday_overtime_hours=Decimal(str(serialized_result["time_summary"]["holiday_overtime_hours"])),
                total_net_work_hours=Decimal(str(serialized_result["time_summary"]["total_net_work_hours"]))
            )
            
            # ComplianceAlert 객체 생성
            compliance_alerts = []
            for alert_data in serialized_result["compliance_alerts"]:
                compliance_alerts.append(ComplianceAlert(
                    alert_code=alert_data["alert_code"],
                    message=alert_data["message"],
                    severity=alert_data["severity"]
                ))
            
            # ErrorDetails 객체 생성
            error = None
            if "error" in serialized_result:
                error = ErrorDetails(
                    error_code=serialized_result["error"]["error_code"],
                    message=serialized_result["error"]["message"]
                )
            
            # WorkDayDetail 객체 생성
            daily_details = {}
            for date, detail_data in serialized_result["daily_details"].items():
                daily_details[date] = WorkDayDetail(
                    regular_hours=Decimal(str(detail_data["regular_hours"])),
                    overtime_hours=Decimal(str(detail_data["overtime_hours"])),
                    night_hours=Decimal(str(detail_data["night_hours"])),
                    holiday_hours=Decimal(str(detail_data["holiday_hours"])),
                    holiday_overtime_hours=Decimal(str(detail_data["holiday_overtime_hours"]))
                )
            
            # WorkTimeCalculationResult 객체 생성
            result = WorkTimeCalculationResult(
                processing_mode=serialized_result["processing_mode"],
                time_summary=time_summary,
                warnings=serialized_result["warnings"],
                compliance_alerts=compliance_alerts,
                trace=serialized_result["trace"],
                error=error,
                daily_details=daily_details
            )
            
            # 결과 데이터 저장
            results[policy_name] = {
                "result": result,
                "policy_set": result_data["policy_set"],
                "timestamp": result_data["timestamp"]
            }
        
        # 결과 캐시에 저장
        self.results_cache["loaded_results"] = results
        
        return results


# 사용 예시
if __name__ == "__main__":
    # 정책 시뮬레이터 생성
    simulator = PolicySimulator()
    
    # 입력 데이터 생성
    input_data = TimeCardInputData(
        employee_id="test_employee",
        period="2025-05",
        hire_date=None,
        resignation_date=None,
        records=[
            TimeCardRecord(
                date=datetime.date(2025, 5, 1),
                start_time="09:00",
                end_time="18:00",
                break_time_minutes=60
            ),
            TimeCardRecord(
                date=datetime.date(2025, 5, 2),
                start_time="09:00",
                end_time="20:00",
                break_time_minutes=60
            )
        ]
    )
    
    # 정책 조합 정의
    policy_sets = [
        {
            "calculation_mode.simple_mode": True,
            "company_settings.daily_work_minutes_standard": 480
        },
        {
            "calculation_mode.simple_mode": False,
            "policies.work_classification.overlap_policy": "PRIORITIZE_NIGHT",
            "company_settings.daily_work_minutes_standard": 480
        },
        {
            "calculation_mode.simple_mode": False,
            "policies.work_classification.overlap_policy": "PRIORITIZE_OVERTIME",
            "company_settings.daily_work_minutes_standard": 480
        }
    ]
    
    policy_set_names = ["단순계산모드", "야간우선정책", "연장우선정책"]
    
    # 시뮬레이션 실행
    results = simulator.simulate_across_policies(input_data, policy_sets, policy_set_names)
    
    # 결과 비교
    comparison = simulator.compare_results("단순계산모드", "야간우선정책", detailed=True)
    
    # 추적 로그 요약
    trace_summary = simulator.summarize_policy_trace(results["단순계산모드"]["result"])
    
    # 결과 저장
    output_path = "simulation_results.json"
    simulator.save_simulation_results(results, output_path)
    
    # 결과 로드
    loaded_results = simulator.load_simulation_results(output_path)
    
    print("시뮬레이션 완료!")
    print(f"결과 저장 경로: {output_path}")
