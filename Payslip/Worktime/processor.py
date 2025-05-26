"""
근로시간 자동 계산 모듈 - 통합 컨트롤러

이 파일은 출결 기반(모드 A)과 타임카드 기반(모드 B) 계산기를 통합하는 컨트롤러를 구현합니다.
입력 데이터 형식에 따라 적절한 계산기를 선택하고 결과를 표준화된 형식으로 반환합니다.
"""

import logging
from typing import Dict, Any, List, Optional, Union, TypeVar, Type
import datetime
from decimal import Decimal

from .schema import (
    WorkTimeCalculationResult, ErrorDetails, AttendanceInputRecord, AttendanceInputData, 
    TimeCardRecord, TimeCardInputData, AttendanceSummary, SalaryBasis, TimeSummary
)

# 로깅 설정
logger = logging.getLogger(__name__)

# 타입 힌팅을 위한 제네릭 타입
T = TypeVar('T')

class BaseCalculator:
    """
    모든 계산기의 기본 클래스입니다.
    """
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        
    def calculate(self, input_data: Any) -> Dict[str, Any]:
        """
        계산을 실행하는 추상 메서드입니다.
        하위 클래스에서 구현해야 합니다.
        """
        raise NotImplementedError("Subclasses must implement calculate()")


class WorkTimeProcessor:
    """
    근로시간 계산 프로세서 - 듀얼 모드 지원
    
    이 클래스는 입력 데이터 형식에 따라 적절한 계산기(출결 기반 또는 타임카드 기반)를 
    선택하고 결과를 표준화된 형식으로 반환합니다.
    """

    def __init__(self, settings: Dict[str, Any]):
        """
        WorkTimeProcessor 초기화.

        Args:
            settings: 회사별 및 모듈 운영 설정을 담은 딕셔너리.
        """
        self.settings = settings
        
        # 출결 기반 계산기 초기화
        from .attendance import AttendanceBasedCalculator
        self.attendance_calculator = AttendanceBasedCalculator(settings)
        
        # 타임카드 기반 계산기 초기화 (필요시 주석 해제)
        # from .calculator import TimeCardBasedCalculator
        # self.timecard_calculator = TimeCardBasedCalculator(settings)
        
        logger.info(f"WorkTimeProcessor initialized with company_id: {settings.get('company_id')}")

    def _detect_input_mode(self, input_data: List[Dict[str, Any]]) -> str:
        """
        입력 데이터 형식을 분석하여 적절한 처리 모드를 감지합니다.

        Args:
            input_data: 입력 데이터 리스트

        Returns:
            str: 감지된 모드 ("attendance", "timecard", "unknown")
        """
        if not input_data:
            return "unknown"
        
        # 첫 번째 레코드로 판단
        first_record = input_data[0]
        
        # 출결 기반 모드 (모드 A) 감지
        if "status_code" in first_record:
            return "attendance"
        
        # 타임카드 기반 모드 (모드 B) 감지
        if "start_time" in first_record or "end_time" in first_record:
            return "timecard"
        
        return "unknown"

    def _validate_and_convert_input(self, input_data: List[Dict[str, Any]], 
                                   model_class: Type[T], mode: str, **kwargs) -> Union[T, ErrorDetails]:
        """
        입력 데이터를 검증하고 적절한 모델 객체로 변환합니다.
        """
        try:
            if mode == "attendance":
                records = [AttendanceInputRecord(**record) for record in input_data]
                # period와 employee_id를 kwargs에서 가져와 모델에 전달
                return model_class(
                    records=records,
                    period=kwargs.get("period", ""),
                    employee_id=kwargs.get("employee_id")
                )
            elif mode == "timecard":
                records = [TimeCardRecord(**record) for record in input_data]
                # period와 employee_id를 kwargs에서 가져와 모델에 전달
                return model_class(
                    records=records,
                    period=kwargs.get("period", ""),
                    employee_id=kwargs.get("employee_id")
                )
            else:
                return ErrorDetails(
                    error_code="INVALID_INPUT_FORMAT",
                    message=f"Unknown input format for mode: {mode}"
                )
        except Exception as e:
            logger.error(f"Input validation error: {str(e)}")
            return ErrorDetails(
                error_code="INPUT_VALIDATION_ERROR",
                message=f"Failed to validate input data: {str(e)}",
                details=str(e)
            )

    def process(self, input_data: List[Dict[str, Any]], period: str, 
           employee_id: Optional[str] = None, mode: Optional[str] = None,
           **kwargs) -> WorkTimeCalculationResult:
        """
        근로시간 계산 처리를 실행합니다.

        Args:
            input_data: 입력 데이터 리스트
            period: 처리 기간 (예: "2025-05")
            employee_id: 직원 ID (선택 사항)
            mode: 처리 모드 (선택 사항, 지정하지 않으면 자동 감지)
            **kwargs: 추가 매개변수

        Returns:
            WorkTimeCalculationResult: 계산 결과
        """
        # 기본 결과 객체 초기화
        result = WorkTimeCalculationResult(
            employee_id=employee_id,
            period=period,
            processing_mode="unknown"
        )

        # 입력 데이터 검증
        if not input_data:
            result.processing_mode = "error"
            result.error = ErrorDetails(
                error_code="EMPTY_INPUT",
                message="Input data is empty"
            )
            return result

        # 처리 모드 결정 (명시적 지정 또는 자동 감지)
        processing_mode = mode if mode else self._detect_input_mode(input_data)
        result.processing_mode = processing_mode

        try:
            # 모드별 처리
            if processing_mode == "attendance":
                # 출결 기반 처리 (모드 A)
                input_model = self._validate_and_convert_input(
                    input_data, AttendanceInputData, processing_mode,
                    period=period, employee_id=employee_id  # 여기에 period와 employee_id 전달
                )

                if isinstance(input_model, ErrorDetails):
                    result.processing_mode = "error"
                    result.error = input_model
                    return result

                input_model.employee_id = employee_id
                input_model.period = period

                # 계산 실행
                calculation_result = self.attendance_calculator.calculate(
                    input_model.records, 
                    {"period": period, "employee_id": employee_id, **kwargs}
                )

                # 결과 매핑
                result.attendance_summary = calculation_result.get("attendance_summary")
                result.salary_basis = calculation_result.get("salary_basis")
                result.warnings = calculation_result.get("warnings", [])

                if "error" in calculation_result:
                    result.processing_mode = "error"
                    result.error = calculation_result["error"]

            elif processing_mode == "timecard":
                # 타임카드 기반 처리 (모드 B)
                # 주석 해제 및 구현
                from .calculator import TimeCardBasedCalculator
                self.timecard_calculator = TimeCardBasedCalculator(self.settings)

                input_model = self._validate_and_convert_input(
                    input_data, TimeCardInputData, processing_mode,
                    period=period, employee_id=employee_id  # 여기에 period와 employee_id 전달
                )

                if isinstance(input_model, ErrorDetails):
                    result.processing_mode = "error"
                    result.error = input_model
                    return result

                # 계산 실행
                calculation_result = self.timecard_calculator.calculate(input_model)

                # 결과 매핑
                result.time_summary = calculation_result.get("time_summary")
                result.daily_calculation_details = calculation_result.get("daily_details")
                result.warnings = calculation_result.get("warnings", [])

                if "error" in calculation_result:
                    result.processing_mode = "error"
                    result.error = calculation_result["error"]

            else:
                # 알 수 없는 모드
                result.processing_mode = "error"
                result.error = ErrorDetails(
                    error_code="UNKNOWN_PROCESSING_MODE",
                    message=f"Unknown processing mode: {processing_mode}"
                )

        except Exception as e:
            # 예외 처리
            logger.error(f"Processing error: {str(e)}", exc_info=True)
            result.processing_mode = "error"
            result.error = ErrorDetails(
                error_code="PROCESSING_ERROR",
                message=f"Error during processing: {str(e)}",
                details=str(e)
            )

        return result