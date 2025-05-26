"""
CLI 인터페이스 모듈

이 모듈은 명령줄 인터페이스를 통해 급여 계산 및 명세서 생성 기능을 제공합니다.
"""
import os
import sys
import typer
from typing_extensions import Annotated
import logging
import json
import datetime
import time # time 모듈은 명시적으로 사용되지 않았으나, 필요시 유지
import glob # glob 모듈은 명시적으로 사용되지 않았으나, 필요시 유지
import re   # re 모듈은 명시적으로 사용되지 않았으나, 필요시 유지
import yaml

# --- sys.path 설정 ---
# 현재 파일(payroll_cli.py)의 디렉토리 (Cli/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 (HR MVP Status and Context Inheritance (4)/)
project_root = os.path.dirname(current_dir)

# 프로젝트 루트를 sys.path에 추가
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- sys.path 설정 완료 ---

# 필요한 모듈 임포트 (수정된 경로)
from Payslip.Payslip.generator import PayslipGenerator
# PayslipCalculator가 Payslip.payroll_calculator_structured.PayrollCalculator를 의미한다고 가정
from Payslip.payroll_calculator_structured import PayrollCalculator as PayslipCalculator
from Payslip.Worktime.schema import TimeCardInputData, TimeCardRecord # work_time_schema.py가 Worktime 폴더 내 schema.py로 가정
from Payslip.policy_manager import PolicyManager

# 로깅 설정
LOG_DIR = "output/logs" # 프로젝트 루트 기준 output/logs
# project_root를 기준으로 절대 경로를 만들어줍니다.
abs_log_dir = os.path.join(project_root, LOG_DIR)
os.makedirs(abs_log_dir, exist_ok=True)
current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
cli_log_file_path = os.path.join(abs_log_dir, f"cli_operations_{current_date_str}.log")

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def setup_logger(name, log_file, level=logging.INFO, add_console_handler=False):
    """로거 설정"""
    logger = logging.getLogger(name)
    if logger.hasHandlers():
        logger.handlers.clear()
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)
    if add_console_handler:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger

operation_logger = setup_logger("CLIOperationLogger", cli_log_file_path, add_console_handler=True)

app = typer.Typer()

def load_settings(settings_filename: str = "settings.yaml") -> dict: # 파일명을 인자로 받도록 변경
    """설정 파일 로드"""
    # 설정 파일 경로를 프로젝트 루트 기준으로 구성
    settings_file_path = os.path.join(project_root, "Config", settings_filename)
    operation_logger.info(f"[INFO] 설정 파일 로딩 시도: {settings_file_path}")
    
    default_settings = {
        "company_info": {
            "company_name": "(주)마누스 컴퍼니 기본값",
            "business_registration_number": "000-00-00000",
            "ceo_name": "기본 대표",
            "company_address": "기본 주소",
            "company_contact": "00-0000-0000",
            "default_pay_date": "매월 25일"
        },
        "output_settings": {
            "json_output_dir": "output/json", # 이 경로는 프로젝트 루트 기준입니다.
            "payroll_output_dir": "output/payroll",
            "payslip_pdf_dir": "output/payslips",
            "payslip_html_dir": "output/payslips",
            "log_dir": LOG_DIR # LOG_DIR은 이미 프로젝트 루트 기준 상대경로로 정의됨
        },
        "yearly_policies": {"2025": {"minimum_wage_hourly": 9860}}, # 예시, 실제 값은 settings.yaml에서 로드
        "default_policy_year": "2025",
        "payslip_settings": {
            "html_template_dir": os.path.join(project_root, "Templates"), # 로컬 템플릿 경로로 수정
            "html_template_name": "payslip_template.html",
            "calculation_message_if_missing": "계산식이 제공되지 않았습니다."
        }
    }
    
    try:
        if os.path.exists(settings_file_path):
            with open(settings_file_path, 'r', encoding='utf-8') as f:
                loaded_settings = yaml.safe_load(f)
                if loaded_settings:
                    operation_logger.info(f"[INFO] 설정 파일 '{settings_file_path}' 로딩 완료.")
                    # 기본 설정에 로드된 설정을 병합 (깊은 병합 방식 개선)
                    def merge_settings(default, loaded):
                        for key, value in loaded.items():
                            if isinstance(value, dict) and key in default and isinstance(default[key], dict):
                                merge_settings(default[key], value)
                            else:
                                default[key] = value
                    merged_settings = default_settings.copy() # 기본값 복사 후 병합
                    merge_settings(merged_settings, loaded_settings)
                    return merged_settings
                else:
                    operation_logger.warning(f"[WARNING] 설정 파일 '{settings_file_path}'이 비어있습니다. 기본 설정을 사용합니다.")
        else:
            operation_logger.warning(f"[WARNING] 설정 파일 '{settings_file_path}'을(를) 찾을 수 없습니다. 기본 설정을 사용합니다.")
    except yaml.YAMLError as e:
        operation_logger.error(f"[ERROR] 설정 파일 '{settings_file_path}' 파싱 중 YAML 오류: {e}. 기본 설정을 사용합니다.", exc_info=True)
    except Exception as e:
        operation_logger.error(f"[ERROR] 설정 파일 '{settings_file_path}' 로드 중 예기치 않은 오류: {e}. 기본 설정을 사용합니다.", exc_info=True)
    
    operation_logger.info(f"[INFO] 기본 설정 사용됨.")
    return default_settings

@app.command()
def calculate(
    employee_id: Annotated[str, typer.Option(help="급여를 계산할 직원 ID (예: EMP001)")],
    year_month: Annotated[str, typer.Option(help="급여 계산 대상 연월 (YYYY-MM 형식, 예: 2025-07)")] = datetime.datetime.now().strftime("%Y-%m"),
    input_file: Annotated[str, typer.Option(help="타임카드 입력 파일 경로 (JSON 형식, 프로젝트 루트 기준 상대 경로 또는 절대 경로)")] = None,
    settings_file: Annotated[str, typer.Option(help="사용자 정의 설정 파일 이름 (Config 폴더 내, 예: settings.yaml)")] = "settings.yaml"
) -> None:
    """
    직원의 급여를 계산하고 결과를 JSON 파일로 저장합니다.
    """
    operation_logger.info(f"[INFO] 명령어 실행: calculate, 직원 ID: {employee_id}, 대상 연월: {year_month}, 설정 파일: {settings_file}")
    print(f"급여 계산 시작: 직원 ID {employee_id}, 대상 연월 {year_month}")
    
    settings = load_settings(settings_file) # 설정 파일 인자 전달
    
    # 입력 데이터 준비
    actual_input_file_path = None
    if input_file:
        # input_file이 절대 경로가 아니면 프로젝트 루트 기준으로 경로 조합
        if not os.path.isabs(input_file):
            actual_input_file_path = os.path.join(project_root, input_file)
        else:
            actual_input_file_path = input_file
            
    if actual_input_file_path and os.path.exists(actual_input_file_path):
        operation_logger.info(f"입력 파일에서 데이터 로드: {actual_input_file_path}")
        with open(actual_input_file_path, 'r', encoding='utf-8') as f:
            input_data_dict = json.load(f)
        
        input_data = TimeCardInputData(
            employee_id=input_data_dict.get("employee_id", employee_id),
            period=input_data_dict.get("period", year_month),
            hire_date=datetime.datetime.strptime(input_data_dict.get("hire_date"), "%Y-%m-%d").date() if input_data_dict.get("hire_date") else None,
            resignation_date=datetime.datetime.strptime(input_data_dict.get("resignation_date"), "%Y-%m-%d").date() if input_data_dict.get("resignation_date") else None,
            records=[
                TimeCardRecord(
                    date=datetime.datetime.strptime(record.get("date"), "%Y-%m-%d").date() if record.get("date") else None,
                    start_time=record.get("start_time"),
                    end_time=record.get("end_time"),
                    break_time_minutes=record.get("break_time_minutes", 0),
                    is_holiday=record.get("is_holiday", False)
                )
                for record in input_data_dict.get("records", [])
            ]
        )
    else:
        if input_file: # input_file 경로가 주어졌으나 파일을 찾지 못한 경우
            operation_logger.warning(f"입력 파일 '{actual_input_file_path}'을(를) 찾을 수 없어 예시 데이터를 생성합니다.")
        else: # input_file 경로가 주어지지 않은 경우
            operation_logger.info("입력 파일이 제공되지 않아 예시 데이터를 생성합니다.")

        records = []
        year_month_obj = datetime.datetime.strptime(year_month, "%Y-%m")
        
        current_date = datetime.datetime(year_month_obj.year, year_month_obj.month, 1)
        while current_date.month == year_month_obj.month:
            is_weekend = current_date.weekday() >= 5 # 토(5), 일(6)
            if not is_weekend:
                records.append(TimeCardRecord(
                    date=current_date.date(),
                    start_time="09:00",
                    end_time="18:00",
                    break_time_minutes=60,
                    is_holiday=False
                ))
            current_date += datetime.timedelta(days=1)
        
        input_data = TimeCardInputData(
            employee_id=employee_id,
            period=year_month,
            hire_date=None, # 예시 데이터에는 입사일/퇴사일 미포함 또는 기본값 설정 가능
            resignation_date=None,
            records=records
        )
    
    # 급여 계산
    policy_manager = PolicyManager(settings=settings) # PolicyManager에 settings 전달
    calculator = PayslipCalculator(policy_manager) # 생성자 인자가 policy_manager로 가정
    result = calculator.calculate_payslip(input_data) # 메소드 인자가 input_data로 가정
    
    # 결과 저장
    # output_settings의 경로는 프로젝트 루트 기준 상대 경로이므로, project_root와 join
    payroll_output_dir_relative = settings.get("output_settings", {}).get("payroll_output_dir", "output/payroll")
    abs_payroll_output_dir = os.path.join(project_root, payroll_output_dir_relative)
    os.makedirs(abs_payroll_output_dir, exist_ok=True)
    
    output_filename = f"{employee_id}_{year_month.replace('-', '')}_payroll.json"
    output_path = os.path.join(abs_payroll_output_dir, output_filename)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    
    print(f"급여 계산 완료. 결과 파일: {output_path}")
    operation_logger.info(f"[INFO] 급여 계산 완료. 결과 파일: {output_path}")

@app.command()
def generate_payslip(
    employee_id: Annotated[str, typer.Option(help="급여명세서를 생성할 직원 ID (예: EMP001)")],
    year_month: Annotated[str, typer.Option(help="급여명세서 생성 대상 연월 (YYYY-MM 형식, 예: 2025-07)")],
    payroll_file: Annotated[str, typer.Option(help="급여 계산 결과 파일 경로 (JSON 형식, 프로젝트 루트 기준 상대 경로 또는 절대 경로)")] = None,
    output_dir: Annotated[str, typer.Option(help="PDF/HTML 급여명세서를 저장할 디렉토리 경로 (프로젝트 루트 기준 상대 경로 또는 절대 경로)")] = None,
    html_output: Annotated[bool, typer.Option("--html", help="PDF 외에 HTML 중간 산출물도 함께 저장합니다.")] = False,
    settings_file: Annotated[str, typer.Option(help="사용자 정의 설정 파일 이름 (Config 폴더 내, 예: settings.yaml)")] = "settings.yaml"
) -> None:
    """
    직원의 급여명세서를 생성하고 PDF 파일로 저장합니다.
    """
    operation_logger.info(f"[INFO] 명령어 실행: generate_payslip, 직원 ID: {employee_id}, 대상 연월: {year_month}, 설정 파일: {settings_file}")
    print(f"급여명세서 생성 시작: 직원 ID {employee_id}, 대상 연월 {year_month}")
    
    settings = load_settings(settings_file)
    
    # 급여 계산 결과 파일 경로 결정
    actual_payroll_file_path = None
    if not payroll_file:
        payroll_output_dir_relative = settings.get("output_settings", {}).get("payroll_output_dir", "output/payroll")
        default_payroll_filename = f"{employee_id}_{year_month.replace('-', '')}_payroll.json"
        actual_payroll_file_path = os.path.join(project_root, payroll_output_dir_relative, default_payroll_filename)
    else:
        if not os.path.isabs(payroll_file):
            actual_payroll_file_path = os.path.join(project_root, payroll_file)
        else:
            actual_payroll_file_path = payroll_file
            
    # 급여 계산 결과 로드
    if not os.path.exists(actual_payroll_file_path):
        print(f"오류: 급여 계산 결과 파일을 찾을 수 없습니다: {actual_payroll_file_path}")
        operation_logger.error(f"[ERROR] 급여 계산 결과 파일을 찾을 수 없습니다: {actual_payroll_file_path}")
        return
    
    with open(actual_payroll_file_path, 'r', encoding='utf-8') as f:
        payroll_data = json.load(f) # 이 payroll_data가 PayslipGenerator가 필요로 하는 데이터 형식이어야 함
    
    # 출력 디렉토리 결정
    abs_pdf_output_dir = None
    abs_html_output_dir = None

    if output_dir:
        if not os.path.isabs(output_dir):
            abs_pdf_output_dir = os.path.join(project_root, output_dir)
            abs_html_output_dir = os.path.join(project_root, output_dir)
        else:
            abs_pdf_output_dir = output_dir
            abs_html_output_dir = output_dir
    else:
        pdf_output_dir_relative = settings.get("output_settings", {}).get("payslip_pdf_dir", "output/payslips")
        html_output_dir_relative = settings.get("output_settings", {}).get("payslip_html_dir", "output/payslips")
        abs_pdf_output_dir = os.path.join(project_root, pdf_output_dir_relative)
        abs_html_output_dir = os.path.join(project_root, html_output_dir_relative)

    os.makedirs(abs_pdf_output_dir, exist_ok=True)
    if html_output:
        os.makedirs(abs_html_output_dir, exist_ok=True)
    
    # 급여명세서 생성기 초기화
    company_info = settings.get("company_info", {})
    payslip_gen_settings = settings.get("payslip_settings", {}) # generator 생성자에 settings 전체를 넘길지, 일부만 넘길지 확인 필요
    
    # PayslipGenerator 생성자 인자에 맞게 전달 (기존 코드의 generator 생성자와 다를 수 있음)
    # 기존 코드: PayslipGenerator(company_info, template_dir, template_name, calc_msg_missing, settings)
    # 현재 파일 구조: Payslip/Payslip/generator.py
    # Payslip/Payslip/generator.py의 PayslipGenerator 생성자를 확인하고 인자를 맞춰주세요.
    # 여기서는 settings에서 필요한 값을 추출하여 전달하는 것으로 가정합니다.
    generator = PayslipGenerator(
        company_info=company_info,
        settings=settings # Payslip/Payslip/generator.py의 생성자가 settings 전체를 받는다고 가정
    )
    
    # PDF 파일 경로 결정
    pdf_filename = f"{employee_id}_{year_month.replace('-', '')}_payslip.pdf"
    pdf_path = os.path.join(abs_pdf_output_dir, pdf_filename)
    
    # PDF 생성 (PayslipGenerator의 메소드명과 인자 확인 필요)
    # 기존 코드: generator.generate_pdf(payroll_data, pdf_path) -> (success, error_msg)
    # Payslip/Payslip/generator.py의 generate_pdf 메소드를 확인해주세요.
    # 여기서는 payroll_data와 출력 경로를 인자로 받는다고 가정합니다.
    # 또한, 해당 generator가 html 템플릿 경로 등을 내부적으로 settings에서 참조한다고 가정합니다.
    try:
        # generate_pdf가 파일 경로 대신 파일명만 받을 수도 있고, 성공/실패 여부만 반환할 수도 있음.
        # 아래는 PayslipGenerator가 pdf_path에 직접 저장하고 성공 여부를 bool로 반환한다고 가정
        # Payslip/Payslip/generator.py 에 맞게 수정 필요
        generated_pdf_path = generator.generate_pdf(payroll_data, pdf_output_path=pdf_path) # generator.py의 실제 메소드 시그니처 확인!

        if generated_pdf_path and os.path.exists(generated_pdf_path): # 또는 success bool 값으로 확인
            print(f"PDF 급여명세서 생성 완료: {generated_pdf_path}")
            operation_logger.info(f"[INFO] PDF 급여명세서 생성 완료: {generated_pdf_path}")
        else:
            # generate_pdf가 오류 메시지를 반환하는 경우
            error_msg = "PDF 생성 실패 (generator에서 상세 오류 확인 필요)" # generator.generate_pdf 반환값에 따라 수정
            print(f"오류: PDF 급여명세서 생성 실패: {error_msg}")
            operation_logger.error(f"[ERROR] PDF 급여명세서 생성 실패: {error_msg}")
            
    except Exception as e:
        print(f"오류: PDF 급여명세서 생성 중 예외 발생: {e}")
        operation_logger.error(f"[ERROR] PDF 급여명세서 생성 중 예외 발생: {e}", exc_info=True)
        return # 실패 시 여기서 중단
    
    # HTML 생성 (옵션)
    if html_output:
        # PayslipGenerator의 HTML 생성 메소드 확인 필요
        # 기존 코드: generator.generate_html(payroll_data) -> html_content
        # Payslip/Payslip/generator.py의 generate_html 메소드를 확인해주세요.
        try:
            html_content = generator.generate_html(payroll_data) # generator.py의 실제 메소드 시그니처 확인!
            if html_content:
                html_filename = f"{employee_id}_{year_month.replace('-', '')}_payslip.html"
                html_path = os.path.join(abs_html_output_dir, html_filename)
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                
                print(f"HTML 급여명세서 생성 완료: {html_path}")
                operation_logger.info(f"[INFO] HTML 급여명세서 생성 완료: {html_path}")
            else:
                operation_logger.warning("[WARNING] HTML 생성 결과가 없습니다.")
        except Exception as e:
            print(f"오류: HTML 급여명세서 생성 중 예외 발생: {e}")
            operation_logger.error(f"[ERROR] HTML 급여명세서 생성 중 예외 발생: {e}", exc_info=True)


@app.command()
def end_to_end_test(
    employee_id: Annotated[str, typer.Option(help="테스트할 직원 ID (예: TEST001)")] = "TEST001",
    year_month: Annotated[str, typer.Option(help="테스트 대상 연월 (YYYY-MM 형식, 예: 2025-07)")] = datetime.datetime.now().strftime("%Y-%m"),
    settings_file: Annotated[str, typer.Option(help="사용자 정의 설정 파일 이름 (Config 폴더 내, 예: settings.yaml)")] = "settings.yaml"
) -> None:
    """
    급여 계산부터 명세서 생성까지 전체 흐름을 테스트합니다.
    """
    operation_logger.info(f"[INFO] 명령어 실행: end_to_end_test, 직원 ID: {employee_id}, 대상 연월: {year_month}, 설정 파일: {settings_file}")
    print(f"End-to-End 테스트 시작: 직원 ID {employee_id}, 대상 연월 {year_month}")
    
    # 1. 급여 계산
    print("\n1. 급여 계산 단계")
    # end_to_end_test는 input_file을 기본값(None)으로 사용하고, settings_file을 전달합니다.
    calculate(employee_id=employee_id, year_month=year_month, input_file=None, settings_file=settings_file)
    
    # 2. 급여명세서 생성
    print("\n2. 급여명세서 생성 단계")
    # payroll_file 인자를 None으로 하여 calculate에서 생성된 파일을 자동으로 찾도록 하고,
    # output_dir도 None으로 하여 기본 설정 경로를 사용하도록 합니다.
    # settings_file을 전달합니다.
    generate_payslip(employee_id=employee_id, year_month=year_month, payroll_file=None, output_dir=None, html_output=True, settings_file=settings_file)
    
    print("\nEnd-to-End 테스트 완료!")
    operation_logger.info(f"[INFO] End-to-End 테스트 완료: 직원 ID {employee_id}, 대상 연월 {year_month}")

if __name__ == "__main__":
    app()