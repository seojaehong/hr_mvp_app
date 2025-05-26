"""
정책 관리자 클래스

설정 파일에서 정책을 로드하고 관리하는 클래스입니다.
계층적 접근(dot notation)을 지원합니다.
"""

import os
import yaml
import logging
import datetime
from decimal import Decimal
from typing import Dict, List, Any, Optional, Union

# 로거 설정
logger = logging.getLogger(__name__)

class PolicyManager:
    """
    정책 관리자 클래스
    
    설정 파일에서 정책을 로드하고 관리하는 클래스입니다.
    계층적 접근(dot notation)을 지원합니다.
    """
    
    def __init__(self, settings_path=None, minimum_wage_path=None, holidays_path=None):
        """
        PolicyManager 초기화
        
        Args:
            settings_path: 설정 파일 경로 (기본값: settings.yaml)
            minimum_wage_path: 최저임금 설정 파일 경로 (기본값: minimum_wage.yaml)
            holidays_path: 공휴일 설정 파일 경로 (기본값: holidays.yaml)
        """
        self.settings = {}
        self.minimum_wages = {}
        self.holidays = []
        
        # 기본 경로 설정
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 설정 파일 로드
        if settings_path is None:
            settings_path = os.path.join(base_dir, "settings.yaml")
        self._load_settings(settings_path)
        
        # 최저임금 설정 로드
        if minimum_wage_path is None:
            minimum_wage_path = os.path.join(base_dir, "minimum_wage.yaml")
        self._load_minimum_wages(minimum_wage_path)
        
        # 공휴일 설정 로드
        if holidays_path is None:
            holidays_path = os.path.join(base_dir, "holidays.yaml")
        self._load_holidays(holidays_path)
        
        logger.info("PolicyManager initialized with settings from %s", settings_path)
    
    def _load_settings(self, file_path):
        """
        설정 파일 로드
        
        Args:
            file_path: 설정 파일 경로
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                self.settings = yaml.safe_load(f)
                
                # 단순계산모드 기본값 설정 (사용자 요청에 따라 기본값을 True로 설정)
                if "calculation_mode" not in self.settings:
                    self.settings["calculation_mode"] = {
                        "simple_mode": True,
                        "simple_mode_options": {
                            "overtime_multiplier": 1.5,
                            "holiday_work_method": "HOURLY"
                        }
                    }
                elif "simple_mode" not in self.settings.get("calculation_mode", {}):
                    self.settings.setdefault("calculation_mode", {})["simple_mode"] = True
                    self.settings["calculation_mode"].setdefault("simple_mode_options", {
                        "overtime_multiplier": 1.5,
                        "holiday_work_method": "HOURLY"
                    })
                
                logger.info("Settings loaded from %s", file_path)
        except Exception as e:
            logger.error(f"Failed to load settings from {file_path}: {e}")
            # 기본 설정 생성
            self.settings = {
                "environment": "production",
                "test_mode": False,
                "calculation_mode": {
                    "simple_mode": True,
                    "simple_mode_options": {
                        "overtime_multiplier": 1.5,
                        "holiday_work_method": "HOURLY"
                    }
                },
                "company_settings": {
                    "daily_work_minutes_standard": 480,
                    "night_shift_start_time": "22:00",
                    "night_shift_end_time": "06:00",
                    "weekly_holiday_days": ["Saturday", "Sunday"]
                },
                "policies": {
                    "working_days": {
                        "hire_date": "EXCLUDE_HIRE_DATE",
                        "resignation_date": "EXCLUDE_RESIGNATION_DATE"
                    },
                    "work_classification": {
                        "overlap_policy": "PRIORITIZE_NIGHT",
                        "break_time_policy": "NO_NIGHT_DEDUCTION"
                    },
                    "weekly_holiday": {
                        "min_hours": 15,
                        "allowance_hours": 8,
                        "include_first_week": False
                    },
                    "tardiness_early_leave": {
                        "standard_start_time": "09:00",
                        "standard_end_time": "18:00",
                        "deduction_unit": 30,
                        "apply_deduction": True
                    },
                    "warnings": {
                        "enabled": True,
                        "test_mode_override": True
                    },
                    "validation": {
                        "policy": "LENIENT"
                    }
                }
            }
            logger.warning("Using default settings due to error")
    
    def _load_minimum_wages(self, file_path):
        """
        최저임금 설정 로드
        
        Args:
            file_path: 최저임금 설정 파일 경로
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.minimum_wages = {item['year']: item for item in data.get('minimum_wages', [])}
                logger.info("Minimum wages loaded from %s", file_path)
        except Exception as e:
            logger.error(f"Failed to load minimum wages from {file_path}: {e}")
            # 기본 최저임금 설정
            self.minimum_wages = {
                2023: {"year": 2023, "hourly_rate": 9620, "monthly_equivalent": 2010580},
                2024: {"year": 2024, "hourly_rate": 10000, "monthly_equivalent": 2090000},
                2025: {"year": 2025, "hourly_rate": 10340, "monthly_equivalent": 2161060}
            }
            logger.warning("Using default minimum wages due to error")
    
    def _load_holidays(self, file_path):
        """
        공휴일 설정 로드
        
        Args:
            file_path: 공휴일 설정 파일 경로
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self.holidays = data.get('holidays', [])
                logger.info("Holidays loaded from %s", file_path)
        except Exception as e:
            logger.error(f"Failed to load holidays from {file_path}: {e}")
            # 기본 공휴일 설정 (2025년 주요 공휴일)
            self.holidays = [
                {"date": "2025-01-01", "name": "신정", "type": "national"},
                {"date": "2025-02-01", "name": "설날", "type": "national"},
                {"date": "2025-03-01", "name": "삼일절", "type": "national"},
                {"date": "2025-05-05", "name": "어린이날", "type": "national"},
                {"date": "2025-08-15", "name": "광복절", "type": "national"},
                {"date": "2025-10-03", "name": "개천절", "type": "national"},
                {"date": "2025-12-25", "name": "크리스마스", "type": "national"}
            ]
            logger.warning("Using default holidays due to error")
    
    def get(self, key, default=None):
        """
        정책 값 가져오기 (계층적 접근 지원)
        
        Args:
            key: 정책 키 (예: "policies.working_days.hire_date")
            default: 기본값
        
        Returns:
            정책 값 또는 기본값
        """
        keys = key.split('.')
        value = self.settings
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """
        정책 값 설정 (계층적 접근 지원)
        
        Args:
            key: 정책 키 (예: "policies.working_days.hire_date")
            value: 설정할 값
        """
        keys = key.split('.')
        target = self.settings
        
        # 마지막 키를 제외한 모든 키에 대해 딕셔너리 생성
        for k in keys[:-1]:
            if k not in target or not isinstance(target[k], dict):
                target[k] = {}
            target = target[k]
        
        # 마지막 키에 값 설정
        target[keys[-1]] = value
        logger.debug("Policy value set: %s = %s", key, value)
    
    def save_settings(self, file_path=None):
        """
        설정을 파일에 저장
        
        Args:
            file_path: 저장할 파일 경로 (기본값: 로드한 설정 파일 경로)
        """
        if file_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(base_dir, "settings.yaml")
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(self.settings, f, default_flow_style=False, allow_unicode=True)
            logger.info("Settings saved to %s", file_path)
            return True
        except Exception as e:
            logger.error(f"Failed to save settings to {file_path}: {e}")
            return False
    
    def get_minimum_wage(self, year):
        """
        특정 연도의 최저임금 가져오기
        
        Args:
            year: 연도
        
        Returns:
            최저임금 정보 딕셔너리 또는 None
        """
        return self.minimum_wages.get(year)
    
    def is_holiday(self, date):
        """
        특정 날짜가 공휴일인지 확인
        
        Args:
            date: 확인할 날짜 (datetime.date)
        
        Returns:
            공휴일 여부 (bool)
        """
        date_str = date.strftime("%Y-%m-%d")
        return any(holiday['date'] == date_str for holiday in self.holidays)
    
    def is_weekend(self, date):
        """
        특정 날짜가 주말인지 확인
        
        Args:
            date: 확인할 날짜 (datetime.date)
        
        Returns:
            주말 여부 (bool)
        """
        weekday = date.strftime("%A")
        weekly_holiday_days = self.get("company_settings.weekly_holiday_days", ["Saturday", "Sunday"])
        return weekday in weekly_holiday_days
    
    def is_simple_mode(self):
        """
        단순계산모드 여부 확인
        
        Returns:
            단순계산모드 여부 (bool)
        """
        return self.get("calculation_mode.simple_mode", True)
    
    def get_simple_mode_options(self):
        """
        단순계산모드 옵션 가져오기
        
        Returns:
            단순계산모드 옵션 딕셔너리
        """
        return self.get("calculation_mode.simple_mode_options", {
            "overtime_multiplier": 1.5,
            "holiday_work_method": "HOURLY"
        })
    
    def get_validation_policy(self):
        """
        유효성 검사 정책 가져오기
        
        Returns:
            ValidationPolicy Enum 값 또는 문자열
        """
        policy_str = self.get("policies.validation.policy", "LENIENT")
        
        # Enum 클래스가 정의되어 있는 경우 Enum 값 반환
        try:
            from payslip.policy_definitions import ValidationPolicy
            return ValidationPolicy[policy_str]
        except (ImportError, KeyError, AttributeError):
            # Enum 클래스가 없거나 해당 값이 없는 경우 문자열 반환
            return policy_str
    
    def get_overlapping_work_policy(self):
        """
        중복 근로시간 처리 정책 가져오기
        
        Returns:
            OverlappingWorkPolicy Enum 값 또는 문자열
        """
        policy_str = self.get("policies.work_classification.overlap_policy", "PRIORITIZE_NIGHT")
        
        # Enum 클래스가 정의되어 있는 경우 Enum 값 반환
        try:
            from payslip.policy_definitions import OverlappingWorkPolicy
            return OverlappingWorkPolicy[policy_str]
        except (ImportError, KeyError, AttributeError):
            # Enum 클래스가 없거나 해당 값이 없는 경우 문자열 반환
            return policy_str
    
    def get_break_time_policy(self):
        """
        휴게시간 처리 정책 가져오기
        
        Returns:
            BreakTimePolicy Enum 값 또는 문자열
        """
        policy_str = self.get("policies.work_classification.break_time_policy", "NO_NIGHT_DEDUCTION")
        
        # Enum 클래스가 정의되어 있는 경우 Enum 값 반환
        try:
            from payslip.policy_definitions import BreakTimePolicy
            return BreakTimePolicy[policy_str]
        except (ImportError, KeyError, AttributeError):
            # Enum 클래스가 없거나 해당 값이 없는 경우 문자열 반환
            return policy_str
    
    def get_weekly_holiday_policy(self):
        """
        주휴수당 정책 가져오기
        
        Returns:
            주휴수당 정책 딕셔너리
        """
        return {
            "min_hours": self.get("policies.weekly_holiday.min_hours", 15),
            "allowance_hours": self.get("policies.weekly_holiday.allowance_hours", 8),
            "include_first_week": self.get("policies.weekly_holiday.include_first_week", False)
        }
    
    def get_tardiness_early_leave_policy(self):
        """
        지각/조퇴 정책 가져오기
        
        Returns:
            지각/조퇴 정책 딕셔너리
        """
        return {
            "standard_start_time": self.get("policies.tardiness_early_leave.standard_start_time", "09:00"),
            "standard_end_time": self.get("policies.tardiness_early_leave.standard_end_time", "18:00"),
            "deduction_unit": self.get("policies.tardiness_early_leave.deduction_unit", 30),
            "apply_deduction": self.get("policies.tardiness_early_leave.apply_deduction", True)
        }
    
    def get_warnings_policy(self):
        """
        경고 메시지 정책 가져오기
        
        Returns:
            경고 메시지 정책 딕셔너리
        """
        return {
            "enabled": self.get("policies.warnings.enabled", True),
            "test_mode_override": self.get("policies.warnings.test_mode_override", True)
        }
    
    def get_working_days_policy(self):
        """
        근무일 처리 정책 가져오기
        
        Returns:
            근무일 처리 정책 딕셔너리
        """
        return {
            "hire_date": self.get("policies.working_days.hire_date", "EXCLUDE_HIRE_DATE"),
            "resignation_date": self.get("policies.working_days.resignation_date", "EXCLUDE_RESIGNATION_DATE")
        }
    
    def get_daily_work_minutes_standard(self):
        """
        일일 표준 근무시간(분) 가져오기
        
        Returns:
            일일 표준 근무시간(분)
        """
        return self.get("company_settings.daily_work_minutes_standard", 480)
    
    def get_night_shift_times(self):
        """
        야간 근무 시간대 가져오기
        
        Returns:
            (야간 시작 시간, 야간 종료 시간) 튜플
        """
        night_start = self.get("company_settings.night_shift_start_time", "22:00")
        night_end = self.get("company_settings.night_shift_end_time", "06:00")
        return night_start, night_end
