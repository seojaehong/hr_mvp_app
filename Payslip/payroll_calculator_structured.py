#payroll_calculator_structured.py
import yaml
import pandas as pd
import logging
import os
from typing import Optional, Dict, Any

# 로깅 설정 (프로젝트 루트에 payroll_calculations.log 생성)
# 이 스크립트(Payslip/...)가 프로젝트 루트에서 실행될 것이므로,
# os.getcwd()를 사용하여 로그 파일 경로를 프로젝트 루트 기준으로 설정
log_file_path = os.path.join(os.getcwd(), "payroll_calculations.log")
try:
    # 로그 핸들러가 중복 추가되는 것을 방지 (스크립트 재실행 시 유용)
    root_logger = logging.getLogger()
    if root_logger.hasHandlers():
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
except Exception as e:
    print(f"로깅 설정 중 오류 발생: {e}")

logger = logging.getLogger(__name__)

class PayrollSettings:
    """급여 계산에 필요한 설정값 관리"""
    def __init__(self, settings_abs_path: str, tax_table_abs_path: str): # 두 파일의 절대 경로를 필수로 받음
        self.settings_path: str = settings_abs_path
        self.income_tax_table_excel_path: str = tax_table_abs_path # 간이세액표 절대 경로 직접 사용
        
        self.config: Dict[str, Any] = {}
        self.tax_table_df: pd.DataFrame = pd.DataFrame()
        self.deduction_rounding_unit: int = 10 # 기본값

        # 보험 및 세금 관련 속성 초기화
        self.national_pension_rate_employee: Optional[float] = None
        self.national_pension_monthly_salary_min: Optional[int] = None
        self.national_pension_monthly_salary_max: Optional[int] = None
        self.health_insurance_rate_employee: Optional[float] = None
        self.health_insurance_monthly_salary_max: Optional[int] = None
        self.health_insurance_monthly_salary_min: Optional[int] = None
        self.long_term_care_insurance_rate_on_health_insurance: Optional[float] = None
        self.employment_insurance_rate_employee: Optional[float] = None

        loaded_config = self._load_settings()
        if loaded_config:
            self.config = loaded_config
            self._initialize_attributes() # YAML 구조에 맞게 속성 초기화
            
            if self.income_tax_table_excel_path: # 경로가 유효한 경우에만 로드
                self.tax_table_df = self._load_tax_table(self.income_tax_table_excel_path)
            else:
                logger.error("간이세액표 경로가 제공되지 않아 로드할 수 없습니다.")
        else:
            logger.error(f"설정 파일 로드 실패. PayrollSettings 초기화 중단: {self.settings_path}")

    def _load_settings(self) -> Dict[str, Any]:
        try:
            with open(self.settings_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    logger.warning(f"설정 파일이 비어있습니다: {self.settings_path}")
                    return {}
                logger.info(f"설정 파일 로드 성공: {self.settings_path}")
                return config
        except FileNotFoundError:
            logger.error(f"설정 파일을 찾을 수 없습니다: {self.settings_path}")
            return {}
        except yaml.YAMLError as e:
            logger.error(f"설정 파일 파싱 오류 ({self.settings_path}): {e}")
            return {}
        except Exception as e:
            logger.error(f"설정 파일 로드 중 알 수 없는 오류 발생 ({self.settings_path}): {e}")
            return {}

    def _initialize_attributes(self):
        # settings_old(v1).yaml 구조에 맞게: 보험 관련 설정은 'rates' 키 하위에 있음
        rates_config = self.config.get("rates", {}) 

        np_config = rates_config.get("national_pension", {})
        self.national_pension_rate_employee = np_config.get("employee_rate", 0.045)
        self.national_pension_monthly_salary_min = np_config.get("monthly_salary_min", 370000)
        self.national_pension_monthly_salary_max = np_config.get("monthly_salary_max", 5900000)

        hi_config = rates_config.get("health_insurance", {})
        self.health_insurance_rate_employee = hi_config.get("employee_rate", 0.03545)
        self.health_insurance_monthly_salary_max = hi_config.get("monthly_salary_max", 127056982)
        self.health_insurance_monthly_salary_min = hi_config.get("monthly_salary_min", 280000)
        self.long_term_care_insurance_rate_on_health_insurance = hi_config.get("long_term_care_rate", 0.1295)

        ei_config = rates_config.get("employment_insurance", {})
        self.employment_insurance_rate_employee = ei_config.get("employee_rate", 0.009)

        # income_tax와 general_settings는 YAML 최상위 레벨에 있음
        # 간이세액표 경로는 __init__에서 직접 받으므로, YAML의 경로는 참조하지 않음 (혼선 방지)
        # it_config = self.config.get("income_tax", {}) 
        # yaml_excel_path = it_config.get("tax_table_excel_path") # 이 부분은 사용 안 함

        gs_config = self.config.get("general_settings", {})
        self.deduction_rounding_unit = gs_config.get("deduction_rounding_unit", 10)

    def _load_tax_table(self, tax_table_file_path: str) -> pd.DataFrame:
        # tax_table_file_path는 __init__에서 전달받은 "절대 경로"를 사용
        path_to_load = tax_table_file_path
        
        logger.info(f"간이세액표 로드 시도 (절대 경로 사용): {path_to_load}")
        try:
            df = pd.read_excel(path_to_load, sheet_name=0, header=4)
            
            salary_min_col_raw = df.columns[0]
            salary_max_col_raw = df.columns[1]
            rename_map = {
                salary_min_col_raw: "salary_min_krw_1000",
                salary_max_col_raw: "salary_max_krw_1000",
            }
            for col_idx, col_name_raw in enumerate(df.columns):
                if isinstance(col_name_raw, int) or (isinstance(col_name_raw, str) and col_name_raw.strip().isdigit()):
                    # 부양가족 수 컬럼 이름 (예: '1', '2', ..., '11', 또는 엑셀에서 숫자로 읽힐 수 있음)
                    # 또는 엑셀 컬럼명이 "공제대상가족의 수[1인]" 같은 형태일 수 있음 -> 이 경우 파싱 로직 추가 필요
                    # 현재 코드는 컬럼명이 정수 형태이거나, 정수로 변환 가능한 문자열이라고 가정
                    try:
                        num_dependents = int(str(col_name_raw).strip())
                        if 1 <= num_dependents <= 11: # 유효한 부양가족 수 범위
                             rename_map[col_name_raw] = f"tax_{num_dependents}_person_krw"
                    except ValueError:
                        logger.debug(f"간이세액표 컬럼명 '{col_name_raw}'은 부양가족 수로 변환 불가하여 무시합니다.")


            df.rename(columns=rename_map, inplace=True)

            # 필수 컬럼 존재 확인
            if "salary_min_krw_1000" not in df.columns or "salary_max_krw_1000" not in df.columns:
                logger.error("간이세액표에 '월급여액(이상)' 또는 '월급여액(미만)'에 해당하는 컬럼을 찾을 수 없습니다.")
                return pd.DataFrame()

            df["salary_min_krw_1000"] = pd.to_numeric(df["salary_min_krw_1000"], errors='coerce')
            df["salary_max_krw_1000"] = pd.to_numeric(df["salary_max_krw_1000"], errors='coerce')
            
            found_tax_cols = []
            for i in range(1, 12): # 1인부터 11인까지
                col_name = f"tax_{i}_person_krw"
                if col_name in df.columns:
                    df[col_name] = pd.to_numeric(df[col_name].astype(str).str.replace(',', '', regex=False), errors='coerce')
                    found_tax_cols.append(col_name)
            
            if not found_tax_cols:
                logger.error("간이세액표에서 유효한 세액 컬럼(tax_N_person_krw)을 찾지 못했습니다.")
                return pd.DataFrame()

            df.dropna(subset=["salary_min_krw_1000"], inplace=True) # 월급여액(이상)은 필수

            df["salary_min_krw"] = df["salary_min_krw_1000"] * 1000
            df["salary_max_krw"] = df["salary_max_krw_1000"].apply(lambda x: x * 1000 if pd.notna(x) else float('inf'))
            
            required_cols = ["salary_min_krw", "salary_max_krw"] + found_tax_cols
            logger.info(f"간이세액표 로드 및 전처리 완료. 사용될 컬럼: {required_cols}")
            return df[required_cols]
        except FileNotFoundError:
            logger.error(f"간이세액표 파일을 찾을 수 없습니다: {path_to_load}")
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"간이세액표 로드 중 오류 발생 ({path_to_load}): {e}")
            return pd.DataFrame()

class PayrollCalculationResult:
    def __init__(self, gross_pay: float, non_taxable_allowance: float, taxable_income: float, total_deductions: float, net_pay: float, details: Dict[str, float]):
        self.gross_pay = gross_pay
        self.non_taxable_allowance = non_taxable_allowance
        self.taxable_income = taxable_income
        self.total_deductions = total_deductions
        self.net_pay = net_pay
        self.details = details
    def __str__(self):
        details_str = "\n".join([f"  {k}: {v:,.0f}원" for k, v in self.details.items()])
        return (
            f"총 급여: {self.gross_pay:,.0f}원\n"
            f"비과세 수당: {self.non_taxable_allowance:,.0f}원\n"
            f"과세 대상 소득 (공제 기준): {self.taxable_income:,.0f}원\n"
            f"공제 내역:\n{details_str}\n"
            f"총 공제액: {self.total_deductions:,.0f}원\n"
            f"실수령액: {self.net_pay:,.0f}원"
        )

class PayrollCalculator:
    def __init__(self, settings: PayrollSettings):
        self.settings = settings
        if not self.settings.config or self.settings.tax_table_df.empty :
             logger.error("PayrollSettings가 올바르게 초기화되지 않았거나 세금 테이블이 비어있습니다. PayrollCalculator 생성을 중단합니다.")
             raise ValueError("PayrollSettings가 올바르게 초기화되지 않았거나 세금 테이블이 비어있습니다.")

    def _round_to_unit(self, value: float, unit: Optional[int]) -> float:
        if unit is None or unit == 0:
            return round(value) 
        return round(value / unit) * unit

    def calculate_national_pension(self, taxable_base_for_insurance: float) -> float:
        min_salary = self.settings.national_pension_monthly_salary_min
        max_salary = self.settings.national_pension_monthly_salary_max
        rate = self.settings.national_pension_rate_employee
        taxable_base = taxable_base_for_insurance
        if taxable_base < min_salary: taxable_base = min_salary
        elif taxable_base > max_salary: taxable_base = max_salary
        pension_contribution = taxable_base * rate
        return self._round_to_unit(pension_contribution, self.settings.deduction_rounding_unit)

    def calculate_health_insurance(self, taxable_base_for_insurance: float) -> tuple[float, float]:
        min_salary = self.settings.health_insurance_monthly_salary_min
        max_salary = self.settings.health_insurance_monthly_salary_max
        hi_rate = self.settings.health_insurance_rate_employee
        ltci_rate = self.settings.long_term_care_insurance_rate_on_health_insurance
        taxable_base = taxable_base_for_insurance
        if taxable_base < min_salary: taxable_base = min_salary
        elif taxable_base > max_salary: taxable_base = max_salary
        health_insurance_premium = taxable_base * hi_rate
        health_insurance_premium = self._round_to_unit(health_insurance_premium, self.settings.deduction_rounding_unit)
        long_term_care_premium = health_insurance_premium * ltci_rate
        long_term_care_premium = self._round_to_unit(long_term_care_premium, self.settings.deduction_rounding_unit)
        return health_insurance_premium, long_term_care_premium

    def calculate_employment_insurance(self, taxable_base_for_insurance: float) -> float:
        rate = self.settings.employment_insurance_rate_employee
        employment_insurance_premium = taxable_base_for_insurance * rate
        return self._round_to_unit(employment_insurance_premium, self.settings.deduction_rounding_unit)

    def calculate_income_tax(self, taxable_income_monthly: float, dependents: int = 1) -> tuple[float, float]:
        tax_table = self.settings.tax_table_df
        income_tax = 0.0
        
        if tax_table.empty:
            logger.warning("간이세액표 DataFrame이 비어있습니다. 세액이 0으로 계산됩니다.")
            return 0.0, 0.0
            
        if dependents > 11: dependents_for_lookup = 11
        elif dependents < 1: dependents_for_lookup = 1
        else: dependents_for_lookup = dependents
        tax_col_name = f"tax_{dependents_for_lookup}_person_krw"

        if tax_col_name not in tax_table.columns:
            logger.warning(f"간이세액표에 부양가족 수 {dependents_for_lookup}인 컬럼('{tax_col_name}')을 찾을 수 없습니다. 사용 가능한 컬럼: {tax_table.columns.tolist()}. 세액이 0으로 계산됩니다.")
            return 0.0, 0.0

        if taxable_income_monthly < 0:
            logger.info(f"과세 소득({taxable_income_monthly:,.0f}원)이 음수이므로 소득세는 0원입니다.")
            return 0.0, 0.0
            
        if "salary_min_krw" not in tax_table.columns or "salary_max_krw" not in tax_table.columns:
            logger.error("간이세액표에 'salary_min_krw' 또는 'salary_max_krw' 컬럼이 없습니다. 세액이 0으로 계산됩니다.")
            return 0.0, 0.0
            
        matched_row = tax_table[
            (tax_table["salary_min_krw"] <= taxable_income_monthly) & 
            (taxable_income_monthly < tax_table["salary_max_krw"])
        ]

        if not matched_row.empty:
            income_tax_val = matched_row[tax_col_name].iloc[0]
            income_tax = float(income_tax_val) if pd.notna(income_tax_val) else 0.0
        else:
            last_row = tax_table.iloc[-1]
            if taxable_income_monthly >= last_row["salary_min_krw"]:
                 income_tax_val = last_row[tax_col_name]
                 income_tax = float(income_tax_val) if pd.notna(income_tax_val) else 0.0
                 logger.info(f"과세 소득({taxable_income_monthly:,.0f}원)이 간이세액표 최고 구간에 해당. 마지막 구간 세액({income_tax:,.0f}원) 적용.")
            elif taxable_income_monthly < tax_table["salary_min_krw"].min():
                income_tax = 0.0
                logger.info(f"과세 소득({taxable_income_monthly:,.0f}원)이 간이세액표 최저 구간 미만. 세액 0원 적용.")
            else:
                logger.warning(f"{taxable_income_monthly:,.0f}원에 해당하는 간이세액표 구간을 찾을 수 없습니다. 세액이 0으로 계산됩니다.")
                income_tax = 0.0
        
        local_income_tax = self._round_to_unit(income_tax * 0.1, self.settings.deduction_rounding_unit)
        return income_tax, local_income_tax

    def calculate_payroll(self, gross_pay: float, non_taxable_allowance: float, dependents: int = 1) -> PayrollCalculationResult:
        taxable_base_for_all_calculations = gross_pay - non_taxable_allowance
        logger.info(f"급여 계산 시작: 총급여 {gross_pay:,.0f}, 비과세 {non_taxable_allowance:,.0f}, 과세대상 {taxable_base_for_all_calculations:,.0f}, 부양가족 {dependents}인")
        np = self.calculate_national_pension(taxable_base_for_all_calculations)
        hi, ltci = self.calculate_health_insurance(taxable_base_for_all_calculations)
        ei = self.calculate_employment_insurance(taxable_base_for_all_calculations)
        it, lit = self.calculate_income_tax(taxable_base_for_all_calculations, dependents=dependents)
        deduction_details = {
            "national_pension": np, "health_insurance": hi, "long_term_care_insurance": ltci,
            "employment_insurance": ei, "income_tax": it, "local_income_tax": lit
        }
        total_deductions = sum(deduction_details.values())
        net_pay = gross_pay - total_deductions
        logger.info(f"급여 계산 완료: 총공제액 {total_deductions:,.0f}, 실수령액 {net_pay:,.0f}")
        return PayrollCalculationResult(
            gross_pay=gross_pay, non_taxable_allowance=non_taxable_allowance,
            taxable_income=taxable_base_for_all_calculations, total_deductions=total_deductions,
            net_pay=net_pay, details=deduction_details # 수정: details -> deduction_details
        )

if __name__ == "__main__":
    # 현재 작업 디렉토리 (이 스크립트를 프로젝트 루트에서 실행한다고 가정)
    project_root_from_cwd = os.getcwd()
    logger.info(f"현재 작업 디렉토리 (프로젝트 루트여야 함): {project_root_from_cwd}")

    # 1. 설정 파일(settings_old(v1).yaml)의 "절대 경로"
    #    노무사님께서 제공해주신 경로를 직접 사용합니다.
    settings_yaml_abs_path = r"C:\Users\iceam\Downloads\HR MVP Status and Context Inheritance (4)\Config\settings_old(v1).yaml"
    
    # 2. 간이세액표 엑셀 파일의 "절대 경로"
    #    노무사님께서 제공해주신 경로를 직접 사용합니다.
    tax_table_excel_abs_path = r"C:\Users\iceam\Downloads\HR MVP Status and Context Inheritance (4)\data\근로소득_간이세액표(조견표).xlsx"

    logger.info(f"PayrollCalculator 테스트 시작 (if __name__ == '__main__')")
    logger.info(f"사용할 설정 파일 절대 경로: {settings_yaml_abs_path}")
    logger.info(f"사용할 간이세액표 절대 경로: {tax_table_excel_abs_path}")
    
    # PayrollSettings 객체 생성 시 settings_path와 tax_table_abs_path를 모두 전달
    settings = PayrollSettings(
        settings_abs_path=settings_yaml_abs_path,
        tax_table_abs_path=tax_table_excel_abs_path
    )
    
    if not settings.config: 
        logger.error("테스트 중단: 설정 객체(settings.config)가 초기화되지 않았습니다.")
    elif settings.tax_table_df.empty:
        logger.error("테스트 중단: 세금 테이블(간이세액표)이 비어있거나 로드에 실패했습니다.")
    else:
        try:
            calculator = PayrollCalculator(settings)
            
            test_gross_pay = 3000000.0
            test_non_taxable = 200000.0
            test_dependents = 1
            
            logger.info(f"테스트 입력값: 총급여={test_gross_pay:,.0f}, 비과세={test_non_taxable:,.0f}, 부양가족수={test_dependents}")
            result = calculator.calculate_payroll(test_gross_pay, test_non_taxable, test_dependents)
            
            print("\n--- 최종 계산 결과 ---")
            print(result)
            logger.info("결과 출력 완료")
        except ValueError as ve: # PayrollCalculator 생성 시 발생할 수 있는 오류
            logger.error(f"PayrollCalculator 생성 또는 실행 중 오류: {ve}")
        except Exception as e:
            logger.error(f"급여 계산 테스트 중 예외 발생: {e}")

    logger.info("PayrollCalculator 테스트 종료")
