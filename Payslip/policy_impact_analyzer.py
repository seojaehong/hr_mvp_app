"""
정책 영향도 분석 및 시각화 도구

정책 변경이 결과에 미치는 영향을 분석하고 시각화하는 도구입니다.
"""

import os
import json
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional, Union, Tuple
from decimal import Decimal

from Payslip.work_time_schema import WorkTimeCalculationResult
from Payslip.policy_simulator import PolicySimulator


class PolicyImpactAnalyzer:
    """
    정책 영향도 분석 클래스
    
    정책 변경이 결과에 미치는 영향을 분석합니다.
    """
    
    def __init__(self):
        """
        정책 영향도 분석기 초기화
        """
        self.impact_metrics = {
            'time_metrics': [
                'regular_hours', 'overtime_hours', 'night_hours', 
                'holiday_hours', 'total_hours', 'total_net_work_hours'
            ],
            'compliance_metrics': [
                'warnings_count', 'critical_alerts_count', 'info_alerts_count'
            ],
            'policy_metrics': [
                'applied_policies_count', 'overridden_policies_count'
            ]
        }
    
    def analyze_impact(self, base_result: Dict[str, Any], comparison_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        정책 영향도 분석
        
        Args:
            base_result: 기준 결과
            comparison_results: 비교 결과 딕셔너리
            
        Returns:
            영향도 분석 결과
        """
        impact_analysis = {
            'base_policy': base_result.get('policy_set_name', 'Base Policy'),
            'comparison_policies': [],
            'time_impact': {},
            'compliance_impact': {},
            'policy_application_impact': {},
            'overall_impact_score': {}
        }
        
        base_time_summary = base_result.get('result').time_summary if base_result.get('result') else None
        
        for policy_name, comparison_data in comparison_results.items():
            comparison_result = comparison_data.get('result')
            if not comparison_result:
                continue
            
            # 정책 정보 추가
            policy_info = {
                'name': policy_name,
                'description': comparison_data.get('description', '')
            }
            impact_analysis['comparison_policies'].append(policy_info)
            
            # 시간 영향도 분석
            time_impact = self._analyze_time_impact(base_time_summary, comparison_result.time_summary)
            impact_analysis['time_impact'][policy_name] = time_impact
            
            # 컴플라이언스 영향도 분석
            compliance_impact = self._analyze_compliance_impact(
                base_result.get('result').warnings if base_result.get('result') else [],
                comparison_result.warnings
            )
            impact_analysis['compliance_impact'][policy_name] = compliance_impact
            
            # 정책 적용 영향도 분석
            policy_application_impact = self._analyze_policy_application_impact(
                base_result.get('result').trace if base_result.get('result') else [],
                comparison_result.trace
            )
            impact_analysis['policy_application_impact'][policy_name] = policy_application_impact
            
            # 종합 영향도 점수 계산
            overall_score = self._calculate_overall_impact_score(
                time_impact, compliance_impact, policy_application_impact
            )
            impact_analysis['overall_impact_score'][policy_name] = overall_score
        
        return impact_analysis
    
    def _analyze_time_impact(self, base_summary, comparison_summary) -> Dict[str, Any]:
        """
        시간 영향도 분석
        
        Args:
            base_summary: 기준 시간 요약
            comparison_summary: 비교 시간 요약
            
        Returns:
            시간 영향도 분석 결과
        """
        if not base_summary or not comparison_summary:
            return {'error': 'Missing time summary data'}
        
        impact = {}
        
        for metric in self.impact_metrics['time_metrics']:
            if hasattr(base_summary, metric) and hasattr(comparison_summary, metric):
                base_value = getattr(base_summary, metric)
                comparison_value = getattr(comparison_summary, metric)
                
                absolute_diff = comparison_value - base_value
                
                # 0으로 나누기 방지
                if base_value == 0:
                    percentage_diff = 100 if comparison_value > 0 else 0
                else:
                    percentage_diff = (absolute_diff / base_value) * 100
                
                impact[metric] = {
                    'base_value': float(base_value),
                    'comparison_value': float(comparison_value),
                    'absolute_diff': float(absolute_diff),
                    'percentage_diff': float(percentage_diff),
                    'impact_level': self._determine_impact_level(percentage_diff)
                }
        
        # 종합 시간 영향도 점수 계산
        impact['overall_time_impact_score'] = self._calculate_time_impact_score(impact)
        
        return impact
    
    def _analyze_compliance_impact(self, base_warnings, comparison_warnings) -> Dict[str, Any]:
        """
        컴플라이언스 영향도 분석
        
        Args:
            base_warnings: 기준 경고 목록
            comparison_warnings: 비교 경고 목록
            
        Returns:
            컴플라이언스 영향도 분석 결과
        """
        base_warnings = base_warnings or []
        comparison_warnings = comparison_warnings or []
        
        # 경고 유형별 카운트
        base_warning_counts = self._count_warnings_by_type(base_warnings)
        comparison_warning_counts = self._count_warnings_by_type(comparison_warnings)
        
        impact = {
            'warning_counts': {
                'base': base_warning_counts,
                'comparison': comparison_warning_counts
            },
            'new_warnings': [],
            'resolved_warnings': [],
            'persisting_warnings': []
        }
        
        # 새로운 경고, 해결된 경고, 지속되는 경고 식별
        base_warning_messages = {w.get('message', ''): w for w in base_warnings}
        comparison_warning_messages = {w.get('message', ''): w for w in comparison_warnings}
        
        for message, warning in comparison_warning_messages.items():
            if message not in base_warning_messages:
                impact['new_warnings'].append(warning)
        
        for message, warning in base_warning_messages.items():
            if message not in comparison_warning_messages:
                impact['resolved_warnings'].append(warning)
            else:
                impact['persisting_warnings'].append(warning)
        
        # 컴플라이언스 영향도 점수 계산
        impact['compliance_impact_score'] = self._calculate_compliance_impact_score(
            len(base_warnings), len(comparison_warnings),
            len(impact['new_warnings']), len(impact['resolved_warnings'])
        )
        
        return impact
    
    def _analyze_policy_application_impact(self, base_trace, comparison_trace) -> Dict[str, Any]:
        """
        정책 적용 영향도 분석
        
        Args:
            base_trace: 기준 추적 로그
            comparison_trace: 비교 추적 로그
            
        Returns:
            정책 적용 영향도 분석 결과
        """
        base_trace = base_trace or []
        comparison_trace = comparison_trace or []
        
        # 정책 적용 항목 추출
        base_policy_entries = [entry for entry in base_trace if entry.get('type') == 'policy_applied']
        comparison_policy_entries = [entry for entry in comparison_trace if entry.get('type') == 'policy_applied']
        
        # 정책 키별 적용 항목 그룹화
        base_policies = self._group_policy_entries_by_key(base_policy_entries)
        comparison_policies = self._group_policy_entries_by_key(comparison_policy_entries)
        
        impact = {
            'policy_counts': {
                'base': len(base_policies),
                'comparison': len(comparison_policies)
            },
            'new_policies': [],
            'removed_policies': [],
            'modified_policies': [],
            'unchanged_policies': []
        }
        
        # 새로운 정책, 제거된 정책, 수정된 정책, 변경 없는 정책 식별
        for key, entries in comparison_policies.items():
            if key not in base_policies:
                impact['new_policies'].append({
                    'key': key,
                    'entries': entries
                })
            elif base_policies[key] != entries:
                impact['modified_policies'].append({
                    'key': key,
                    'base_entries': base_policies[key],
                    'comparison_entries': entries
                })
            else:
                impact['unchanged_policies'].append({
                    'key': key,
                    'entries': entries
                })
        
        for key, entries in base_policies.items():
            if key not in comparison_policies:
                impact['removed_policies'].append({
                    'key': key,
                    'entries': entries
                })
        
        # 정책 적용 영향도 점수 계산
        impact['policy_application_impact_score'] = self._calculate_policy_application_impact_score(
            len(impact['new_policies']), len(impact['removed_policies']),
            len(impact['modified_policies']), len(impact['unchanged_policies'])
        )
        
        return impact
    
    def _count_warnings_by_type(self, warnings) -> Dict[str, int]:
        """
        경고 유형별 카운트
        
        Args:
            warnings: 경고 목록
            
        Returns:
            경고 유형별 카운트
        """
        counts = {
            'critical': 0,
            'warning': 0,
            'info': 0,
            'total': len(warnings)
        }
        
        for warning in warnings:
            severity = warning.get('severity', 'warning').lower()
            if severity in counts:
                counts[severity] += 1
        
        return counts
    
    def _group_policy_entries_by_key(self, policy_entries) -> Dict[str, List[Dict[str, Any]]]:
        """
        정책 키별 적용 항목 그룹화
        
        Args:
            policy_entries: 정책 적용 항목 목록
            
        Returns:
            정책 키별 적용 항목 그룹
        """
        grouped = {}
        
        for entry in policy_entries:
            key = entry.get('policy_key', '')
            if key:
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(entry)
        
        return grouped
    
    def _determine_impact_level(self, percentage_diff) -> str:
        """
        영향도 수준 결정
        
        Args:
            percentage_diff: 백분율 차이
            
        Returns:
            영향도 수준 (high, medium, low, none)
        """
        abs_diff = abs(percentage_diff)
        
        if abs_diff >= 20:
            return 'high'
        elif abs_diff >= 10:
            return 'medium'
        elif abs_diff > 0:
            return 'low'
        else:
            return 'none'
    
    def _calculate_time_impact_score(self, time_impact) -> float:
        """
        시간 영향도 점수 계산
        
        Args:
            time_impact: 시간 영향도 분석 결과
            
        Returns:
            시간 영향도 점수 (0-100)
        """
        # 주요 메트릭에 가중치 부여
        weights = {
            'total_net_work_hours': 0.4,
            'regular_hours': 0.2,
            'overtime_hours': 0.2,
            'night_hours': 0.1,
            'holiday_hours': 0.1
        }
        
        score = 0
        total_weight = 0
        
        for metric, weight in weights.items():
            if metric in time_impact:
                impact_level = time_impact[metric]['impact_level']
                
                # 영향도 수준에 따른 점수 부여
                level_score = {
                    'high': 100,
                    'medium': 60,
                    'low': 30,
                    'none': 0
                }.get(impact_level, 0)
                
                score += level_score * weight
                total_weight += weight
        
        # 가중치 합계로 나누어 정규화
        if total_weight > 0:
            score = score / total_weight
        
        return score
    
    def _calculate_compliance_impact_score(self, base_count, comparison_count, new_count, resolved_count) -> float:
        """
        컴플라이언스 영향도 점수 계산
        
        Args:
            base_count: 기준 경고 수
            comparison_count: 비교 경고 수
            new_count: 새로운 경고 수
            resolved_count: 해결된 경고 수
            
        Returns:
            컴플라이언스 영향도 점수 (0-100)
        """
        # 경고 수 변화에 따른 기본 점수
        if comparison_count > base_count:
            base_score = 70  # 경고 증가 (부정적 영향)
        elif comparison_count < base_count:
            base_score = 30  # 경고 감소 (긍정적 영향)
        else:
            base_score = 50  # 경고 수 동일
        
        # 새로운 경고와 해결된 경고에 따른 조정
        adjustment = 0
        
        if base_count > 0:
            # 해결된 경고 비율에 따른 긍정적 조정 (최대 -30)
            resolved_ratio = resolved_count / base_count
            adjustment -= resolved_ratio * 30
        
        if comparison_count > 0:
            # 새로운 경고 비율에 따른 부정적 조정 (최대 +30)
            new_ratio = new_count / comparison_count
            adjustment += new_ratio * 30
        
        # 최종 점수 계산 (0-100 범위로 제한)
        score = max(0, min(100, base_score + adjustment))
        
        return score
    
    def _calculate_policy_application_impact_score(self, new_count, removed_count, modified_count, unchanged_count) -> float:
        """
        정책 적용 영향도 점수 계산
        
        Args:
            new_count: 새로운 정책 수
            removed_count: 제거된 정책 수
            modified_count: 수정된 정책 수
            unchanged_count: 변경 없는 정책 수
            
        Returns:
            정책 적용 영향도 점수 (0-100)
        """
        total_count = new_count + removed_count + modified_count + unchanged_count
        
        if total_count == 0:
            return 0
        
        # 변경된 정책 비율에 따른 점수
        changed_ratio = (new_count + removed_count + modified_count) / total_count
        
        # 변경 비율이 높을수록 영향도가 높음
        score = changed_ratio * 100
        
        return score
    
    def _calculate_overall_impact_score(self, time_impact, compliance_impact, policy_application_impact) -> float:
        """
        종합 영향도 점수 계산
        
        Args:
            time_impact: 시간 영향도 분석 결과
            compliance_impact: 컴플라이언스 영향도 분석 결과
            policy_application_impact: 정책 적용 영향도 분석 결과
            
        Returns:
            종합 영향도 점수 (0-100)
        """
        # 각 영역별 영향도 점수에 가중치 부여
        weights = {
            'time': 0.5,
            'compliance': 0.3,
            'policy_application': 0.2
        }
        
        time_score = time_impact.get('overall_time_impact_score', 0)
        compliance_score = compliance_impact.get('compliance_impact_score', 0)
        policy_application_score = policy_application_impact.get('policy_application_impact_score', 0)
        
        # 가중 평균 계산
        overall_score = (
            time_score * weights['time'] +
            compliance_score * weights['compliance'] +
            policy_application_score * weights['policy_application']
        )
        
        return overall_score


class PolicyVisualizationTool:
    """
    정책 시각화 도구 클래스
    
    정책 영향도 분석 결과를 시각화합니다.
    """
    
    def __init__(self, output_dir: str = '.'):
        """
        정책 시각화 도구 초기화
        
        Args:
            output_dir: 출력 디렉토리 경로
        """
        self.output_dir = output_dir
        self.color_palette = {
            'regular': '#4285F4',  # 파란색
            'overtime': '#EA4335',  # 빨간색
            'night': '#FBBC05',    # 노란색
            'holiday': '#34A853',  # 초록색
            'total': '#673AB7',    # 보라색
            'base': '#757575',     # 회색
            'high': '#D32F2F',     # 진한 빨간색
            'medium': '#FFA000',   # 주황색
            'low': '#388E3C',      # 진한 초록색
            'none': '#BDBDBD'      # 연한 회색
        }
        
        # 출력 디렉토리 생성
        os.mak
(Content truncated due to size limit. Use line ranges to read in chunks)