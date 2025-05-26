"""
정책 템플릿 생성기 및 문서화 도구

정책 설정 예시를 자동 문서화 및 시각화하기 위한 도구를 제공합니다.
"""

import os
import yaml
import json
from typing import Dict, Any, List, Optional, Union
import datetime

def generate_default_settings_yaml(output_path: str = None) -> str:
    """
    기본 정책 설정 YAML 파일 생성
    
    Args:
        output_path: 출력 파일 경로 (기본값: settings_template.yaml)
        
    Returns:
        생성된 파일 경로
    """
    if output_path is None:
        output_path = "settings_template.yaml"
    
    settings = {
        # 기본 설정
        "environment": {
            "value": "production",
            "description": "실행 환경 (production, development, test)",
            "options": ["production", "development", "test"]
        },
        "test_mode": {
            "value": False,
            "description": "테스트 모드 활성화 여부",
            "options": [True, False]
        },
        
        # 계산 모드 설정
        "calculation_mode": {
            "simple_mode": {
                "value": True,
                "description": "단순계산모드 활성화 여부 (true: 단순계산, false: 정책 기반 상세 계산)",
                "options": [True, False]
            },
            "simple_mode_options": {
                "overtime_multiplier": {
                    "value": 1.5,
                    "description": "연장근로 배수",
                    "range": [1.0, 2.0]
                },
                "holiday_work_method": {
                    "value": "HOURLY",
                    "description": "휴일근로 계산 방식 (HOURLY: 시간당 계산, DAILY: 일할계산)",
                    "options": ["HOURLY", "DAILY"]
                }
            }
        },
        
        # 회사 설정
        "company_settings": {
            "daily_work_minutes_standard": {
                "value": 480,
                "description": "일일 표준 근로시간 (분)",
                "range": [0, 1440]
            },
            "night_shift_start_time": {
                "value": "22:00",
                "description": "야간근로 시작 시간",
                "format": "HH:MM"
            },
            "night_shift_end_time": {
                "value": "06:00",
                "description": "야간근로 종료 시간",
                "format": "HH:MM"
            },
            "weekly_holiday_days": {
                "value": ["Saturday", "Sunday"],
                "description": "주휴일 (요일)",
                "options": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            }
        },
        
        # 정책 설정
        "policies": {
            "working_days": {
                "hire_date": {
                    "value": "EXCLUDE_HIRE_DATE",
                    "description": "입사일 처리 방식",
                    "options": ["INCLUDE_HIRE_DATE", "EXCLUDE_HIRE_DATE"]
                },
                "resignation_date": {
                    "value": "EXCLUDE_RESIGNATION_DATE",
                    "description": "퇴사일 처리 방식",
                    "options": ["INCLUDE_RESIGNATION_DATE", "EXCLUDE_RESIGNATION_DATE"]
                }
            },
            "work_classification": {
                "overlap_policy": {
                    "value": "PRIORITIZE_NIGHT",
                    "description": "중복 근로시간 처리 정책",
                    "options": ["PRIORITIZE_NIGHT", "PRIORITIZE_OVERTIME", "SEPARATE_CALCULATION"]
                },
                "break_time_policy": {
                    "value": "NO_NIGHT_DEDUCTION",
                    "description": "휴게 시간 처리 정책",
                    "options": ["DEDUCT_FROM_ALL", "NO_NIGHT_DEDUCTION", "PROPORTIONAL_DEDUCTION"]
                }
            },
            "weekly_holiday": {
                "min_hours": {
                    "value": 15,
                    "description": "주휴수당 발생 최소 시간",
                    "range": [0, 40]
                },
                "allowance_hours": {
                    "value": 8,
                    "description": "주휴수당 시간",
                    "range": [0, 24]
                },
                "include_first_week": {
                    "value": False,
                    "description": "입사 첫 주 주휴수당 포함 여부",
                    "options": [True, False]
                }
            },
            "tardiness_early_leave": {
                "standard_start_time": {
                    "value": "09:00",
                    "description": "표준 출근 시간",
                    "format": "HH:MM"
                },
                "standard_end_time": {
                    "value": "18:00",
                    "description": "표준 퇴근 시간",
                    "format": "HH:MM"
                },
                "deduction_unit": {
                    "value": 30,
                    "description": "공제 단위 (분)",
                    "options": [10, 15, 30, 60]
                },
                "apply_deduction": {
                    "value": True,
                    "description": "지각/조퇴 공제 적용 여부",
                    "options": [True, False]
                }
            },
            "validation": {
                "policy": {
                    "value": "LENIENT",
                    "description": "유효성 검사 정책",
                    "options": ["STRICT", "LENIENT"]
                }
            },
            "warnings": {
                "enabled": {
                    "value": True,
                    "description": "경고 메시지 활성화 여부",
                    "options": [True, False]
                },
                "test_mode_override": {
                    "value": True,
                    "description": "테스트 모드에서 경고 메시지 오버라이드 여부",
                    "options": [True, False]
                }
            }
        },
        
        # 컴플라이언스 알림 설정
        "compliance_alerts": {
            "severity_levels": {
                "value": ["info", "warning", "critical"],
                "description": "알림 심각도 레벨",
                "options": ["info", "warning", "critical"]
            },
            "break_time_rules": {
                "min_break_minutes_per_hours": {
                    "value": 30,
                    "description": "시간당 최소 휴게시간 (분)",
                    "range": [0, 60]
                },
                "severity": {
                    "value": "warning",
                    "description": "휴게시간 부족 알림 심각도",
                    "options": ["info", "warning", "critical"]
                }
            },
            "night_work_rules": {
                "max_consecutive_night_shifts": {
                    "value": 5,
                    "description": "최대 연속 야간근무 일수",
                    "range": [1, 14]
                },
                "severity": {
                    "value": "warning",
                    "description": "야간근무 제한 초과 알림 심각도",
                    "options": ["info", "warning", "critical"]
                }
            }
        }
    }
    
    # 메타데이터 제거하고 실제 값만 추출
    clean_settings = _extract_values(settings)
    
    # YAML 파일 생성
    with open(output_path, 'w', encoding='utf-8') as f:
        # 헤더 추가
        f.write("# =========================================================\n")
        f.write("# 정책 설정 파일\n")
        f.write("# 생성일시: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "\n")
        f.write("# =========================================================\n\n")
        
        # 각 섹션별로 주석과 함께 YAML 작성
        _write_yaml_section(f, settings, clean_settings)
    
    return output_path

def _extract_values(settings_meta: Dict[str, Any]) -> Dict[str, Any]:
    """
    메타데이터에서 실제 값만 추출
    
    Args:
        settings_meta: 메타데이터가 포함된 설정
        
    Returns:
        실제 값만 포함된 설정
    """
    result = {}
    
    for key, value in settings_meta.items():
        if isinstance(value, dict):
            if "value" in value:
                # 값이 직접 포함된 경우
                result[key] = value["value"]
            else:
                # 중첩된 딕셔너리인 경우
                result[key] = _extract_values(value)
        else:
            # 그 외의 경우 (일반적으로 발생하지 않음)
            result[key] = value
    
    return result

def _write_yaml_section(f, settings_meta: Dict[str, Any], clean_settings: Dict[str, Any], prefix: str = ""):
    """
    YAML 섹션 작성
    
    Args:
        f: 파일 객체
        settings_meta: 메타데이터가 포함된 설정
        clean_settings: 실제 값만 포함된 설정
        prefix: 키 접두사
    """
    for key, value in settings_meta.items():
        full_key = f"{prefix}.{key}" if prefix else key
        
        if isinstance(value, dict) and "value" in value:
            # 값이 직접 포함된 경우
            description = value.get("description", "")
            options = value.get("options", [])
            range_val = value.get("range", [])
            format_val = value.get("format", "")
            
            # 주석 추가
            f.write(f"# {description}\n")
            
            if options:
                f.write(f"# 옵션: {options}\n")
            if range_val:
                f.write(f"# 범위: {range_val[0]} ~ {range_val[1]}\n")
            if format_val:
                f.write(f"# 형식: {format_val}\n")
            
            # 값 작성
            yaml_str = yaml.dump({key: clean_settings[key]}, default_flow_style=False)
            f.write(yaml_str)
            f.write("\n")
        elif isinstance(value, dict):
            # 중첩된 딕셔너리인 경우
            f.write(f"# {key} 설정\n")
            f.write(f"{key}:\n")
            
            # 중첩된 섹션 작성
            nested_prefix = full_key
            for nested_key, nested_value in value.items():
                nested_full_key = f"{nested_prefix}.{nested_key}"
                
                if isinstance(nested_value, dict) and "value" in nested_value:
                    # 값이 직접 포함된 경우
                    description = nested_value.get("description", "")
                    options = nested_value.get("options", [])
                    range_val = nested_value.get("range", [])
                    format_val = nested_value.get("format", "")
                    
                    # 주석 추가
                    f.write(f"  # {description}\n")
                    
                    if options:
                        f.write(f"  # 옵션: {options}\n")
                    if range_val:
                        f.write(f"  # 범위: {range_val[0]} ~ {range_val[1]}\n")
                    if format_val:
                        f.write(f"  # 형식: {format_val}\n")
                    
                    # 값 작성
                    yaml_str = yaml.dump({nested_key: clean_settings[key][nested_key]}, default_flow_style=False)
                    yaml_str = "  " + yaml_str.replace("\n", "\n  ").rstrip("  ")
                    f.write(yaml_str)
                    f.write("\n")
                elif isinstance(nested_value, dict):
                    # 중첩된 딕셔너리인 경우
                    f.write(f"  # {nested_key} 설정\n")
                    f.write(f"  {nested_key}:\n")
                    
                    # 더 중첩된 섹션 작성
                    for deep_key, deep_value in nested_value.items():
                        if isinstance(deep_value, dict) and "value" in deep_value:
                            # 값이 직접 포함된 경우
                            description = deep_value.get("description", "")
                            options = deep_value.get("options", [])
                            range_val = deep_value.get("range", [])
                            format_val = deep_value.get("format", "")
                            
                            # 주석 추가
                            f.write(f"    # {description}\n")
                            
                            if options:
                                f.write(f"    # 옵션: {options}\n")
                            if range_val:
                                f.write(f"    # 범위: {range_val[0]} ~ {range_val[1]}\n")
                            if format_val:
                                f.write(f"    # 형식: {format_val}\n")
                            
                            # 값 작성
                            yaml_str = yaml.dump({deep_key: clean_settings[key][nested_key][deep_key]}, default_flow_style=False)
                            yaml_str = "    " + yaml_str.replace("\n", "\n    ").rstrip("    ")
                            f.write(yaml_str)
                            f.write("\n")
                        elif isinstance(deep_value, dict):
                            # 더 중첩된 딕셔너리인 경우 (필요시 재귀 호출)
                            f.write(f"    # {deep_key} 설정\n")
                            f.write(f"    {deep_key}:\n")
                            
                            for deepest_key, deepest_value in deep_value.items():
                                if isinstance(deepest_value, dict) and "value" in deepest_value:
                                    description = deepest_value.get("description", "")
                                    options = deepest_value.get("options", [])
                                    range_val = deepest_value.get("range", [])
                                    format_val = deepest_value.get("format", "")
                                    
                                    # 주석 추가
                                    f.write(f"      # {description}\n")
                                    
                                    if options:
                                        f.write(f"      # 옵션: {options}\n")
                                    if range_val:
                                        f.write(f"      # 범위: {range_val[0]} ~ {range_val[1]}\n")
                                    if format_val:
                                        f.write(f"      # 형식: {format_val}\n")
                                    
                                    # 값 작성
                                    yaml_str = yaml.dump({deepest_key: clean_settings[key][nested_key][deep_key][deepest_key]}, default_flow_style=False)
                                    yaml_str = "      " + yaml_str.replace("\n", "\n      ").rstrip("      ")
                                    f.write(yaml_str)
                                    f.write("\n")

def generate_policy_schema_json(output_path: str = None) -> str:
    """
    정책 스키마 메타 정보 JSON 파일 생성
    
    Args:
        output_path: 출력 파일 경로 (기본값: policy_schema.json)
        
    Returns:
        생성된 파일 경로
    """
    if output_path is None:
        output_path = "policy_schema.json"
    
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "정책 설정 스키마",
        "description": "정책 기반 시뮬레이션을 위한 설정 스키마",
        "type": "object",
        "properties": {
            "environment": {
                "type": "string",
                "description": "실행 환경 (production, development, test)",
                "enum": ["production", "development", "test"]
            },
            "test_mode": {
                "type": "boolean",
                "description": "테스트 모드 활성화 여부",
                "default": False
            },
            "calculation_mode": {
                "type": "object",
                "description": "계산 모드 설정",
                "properties": {
                    "simple_mode": {
                        "type": "boolean",
                        "description": "단순계산모드 활성화 여부 (true: 단순계산, false: 정책 기반 상세 계산)",
                        "default": True
                    },
                    "simple_mode_options": {
                        "type": "object",
                        "description": "단순계산모드 옵션",
                        "properties": {
                            "overtime_multiplier": {
                                "type": "number",
                                "description": "연장근로 배수",
                                "minimum": 1.0,
                                "maximum": 2.0,
                                "default": 1.5
                            },
                            "holiday_work_method": {
                                "type": "string",
                                "description": "휴일근로 계산 방식 (HOURLY: 시간당 계산, DAILY: 일할계산)",
                                "enum": ["HOURLY", "DAILY"]
(Content truncated due to size limit. Use line ranges to read in chunks)