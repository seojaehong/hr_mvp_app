# cli.py
import typer
from typing_extensions import Annotated
import logging
import os
import json
import datetime
import time # For elapsed time calculation
import glob # For batch processing summary files
import re # For robust filename parsing
import yaml # For loading settings.yaml

# --- 실제 모듈 임포트 --- 
# work_time_module 및 payroll_calculator는 플레이스홀더를 유지 (현재 작업 범위 밖)
try:
    from work_time_module import WorkTimeCalculator
except ImportError as e:
    if 'work_time_module' in str(e).lower(): 
        class WorkTimeCalculator:
            def __init__(self, settings: dict):
                self.settings = settings
                print("[플레이스홀더 알림] 실제 WorkTimeCalculator 모듈을 찾을 수 없어 플레이스홀더를 사용합니다.")
            def process_attendance_file(self, file_path: str) -> dict:
                print(f"[플레이스홀더] process_attendance_file 호출됨: {file_path}")
                return {
                    "EMP001": {
                        "year_month": datetime.datetime.now().strftime("%Y-%m"),
                        "summary": {
                            "total_work_days": 22, "total_work_hours": 176.5,
                            "total_overtime_hours": 12.3, "total_late_days": 1,
                            "total_early_leave_days": 0, "attendance_rate": 100.0
                        },
                        "alerts": [{"type": "lateness", "severity": "info", "count": 1, "message": "1회 지각 기록"}]
                    }
                }
    else:
        logging.getLogger("CLIOperationLogger").critical(f"[CRITICAL] WorkTimeCalculator 로드 중 오류: {e}", exc_info=True)
        raise

try:
    from payroll_calculator import PayrollCalculator
except ImportError as e:
    if 'payroll_calculator' in str(e).lower():
        class PayrollCalculator:
            def __init__(self, company_payroll_settings: dict, year_month_settings: dict = None):
                self.company_settings = company_payroll_settings
                self.year_month_settings = year_month_settings 
                print("[플레이스홀더 알림] 실제 PayrollCalculator 모듈을 찾을 수 없어 플레이스홀더를 사용합니다.")
            def calculate_monthly_payroll(self, employee_id: str, year_month: str, work_time_result: dict) -> dict:
                print(f"[플레이스홀더] calculate_monthly_payroll 호출됨: {employee_id} for {year_month}")
                return {
                    "employee_id": employee_id, "year_month": year_month,
                    "calculation_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "source_summary_file": f"output/json/{employee_id}_{year_month.replace('-', '')}_summary.json",
                    "employee_details": { 
                        "name": f"직원 {employee_id}", "birth_date": "1990-01-01", "email": f"{employee_id.lower()}@example.com",
                        "department": "개발팀", "position": "팀원", "hire_date": "2020-01-01"
                    },
                    "personal_info": {"birth_date": "1990-01-01"}, # 암호화 테스트를 위해 추가
                    "work_summary": work_time_result.get("summary", {}),
                    "pay_date": f"{year_month}-25",
                    "pay_components": {
                        "earnings": {
                            "taxable_breakdown": [{"name": "기본급 (플레이스홀더)", "amount": 3000000, "note": "정규 급여"}],
                            "non_taxable_breakdown": [{"name": "식대보조비 (플레이스홀더)", "amount": 200000, "note": "월 20만원 비과세"}],
                            "total_taxable_earnings": 3000000, "total_non_taxable_earnings": 200000, "gross_pay": 3200000
                        },
                        "deductions": {
                            "social_insurance_breakdown": [
                                {"name": "국민연금 (플레이스홀더)", "amount": 135000, "note": "4.5%"},
                                {"name": "건강보험 (플레이스홀더)", "amount": 110000, "note": "3.545%"}
                            ],
                            "tax_breakdown": [
                                {"name": "소득세 (플레이스홀더)", "amount": 85000, "note": "간이세액표 기준"},
                                {"name": "지방소득세 (플레이스홀더)", "amount": 8500, "note": "소득세의 10%"}
                            ],
                            "other_deductions_breakdown": [],
                            "total_social_insurance_deduction": 245000, "total_tax_deduction": 93500, "total_deductions": 338500
                        }
                    },
                    "net_pay": 2861500, "employer_contributions_summary": {},
                    "processing_details": {"warnings": ["플레이스홀더 계산 결과입니다."]}
                }
    else:
        logging.getLogger("CLIOperationLogger").critical(f"[CRITICAL] PayrollCalculator 로드 중 오류: {e}", exc_info=True)
        raise

# PayslipGenerator, security 모듈, EmailService 실제 임포트
try:
    from payslip.generator import PayslipGenerator
    from payslip.security import generate_password, encrypt_pdf
    from modules.email_service import EmailService # EmailService 임포트 추가
except ImportError as e:
    operation_logger = logging.getLogger("CLIOperationLogger") 
    operation_logger.critical(f"[CRITICAL] 주요 모듈(PayslipGenerator, security, EmailService) 로드 실패: {e}. PYTHONPATH 및 파일 위치를 확인하세요.", exc_info=True)
    print(f"[치명적 오류] 급여명세서 생성, 암호화 또는 이메일 발송 모듈을 로드할 수 없습니다. 프로그램 실행이 불가능합니다.")
    raise typer.Exit(code=1)

# --- 로깅 설정 --- 
LOG_DIR = "output/logs"
os.makedirs(LOG_DIR, exist_ok=True)
current_date_str = datetime.datetime.now().strftime("%Y-%m-%d")
cli_log_file_path = os.path.join(LOG_DIR, f"cli_operations_{current_date_str}.log")
audit_log_file_path = os.path.join(LOG_DIR, f"cli_audit_{current_date_str}.log")
# 이메일 로거를 위한 별도 파일 설정 (선택적)
email_log_file_path = os.path.join(LOG_DIR, f"email_operations_{current_date_str}.log")

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

def setup_logger(name, log_file, level=logging.INFO, add_console_handler=False):
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
audit_logger = setup_logger("CLIAuditLogger", audit_log_file_path)
# EmailService 내부에서 payroll.email 로거를 사용하므로 별도 설정 불필요. 필요시 여기서 레벨 등 조정 가능.
email_logger = setup_logger("payroll.email", email_log_file_path, level=logging.DEBUG) # EmailService 로그 레벨 상세 설정

app = typer.Typer()

def load_settings(settings_file: str = "settings.yaml") -> dict:
    operation_logger.info(f"[INFO] 설정 파일 로딩 시도: {settings_file}")
    default_settings = {
        "company_info": {
            "company_name": "(주)마누스 컴퍼니 기본값", "business_registration_number": "000-00-00000",
            "ceo_name": "기본 대표", "company_address": "기본 주소", "company_contact": "00-0000-0000",
            "default_pay_date": "매월 25일"
        },
        "output_settings": {
            "json_output_dir": "output/json", "payroll_output_dir": "output/payroll",
            "payslip_pdf_dir": "output/payslips", "payslip_html_dir": "output/payslips",
            "log_dir": LOG_DIR
        },
        "yearly_policies": {"2025": {"minimum_wage_hourly": 9860}},
        "default_policy_year": "2025",
        "payslip_settings": {
            "html_template_dir": "/home/ubuntu/upload/templates", 
            "html_template_name": "payslip_template.html",
            "calculation_message_if_missing": "계산식이 제공되지 않았습니다."
        },
        "pdf_encryption": {
            "enabled_by_default": False,
            "password_format": "{birth_date_YYYYMMDD}", 
            "encryption_failure_warning": "경고: PDF 암호화에 실패했습니다. 파일은 암호화되지 않은 상태로 저장됩니다.",
            "user_password_hint": "PDF 비밀번호는 직원의 생년월일 8자리(YYYYMMDD)입니다."
        },
        "email": { # 이메일 기본 설정 추가
            "smtp_server": "", "port": 587, "use_tls": True, "username": "",
            "password_env": "SMTP_PASSWORD", 
            "templates_dir": "templates/email",
            "default_template_name": "default_payslip_email.html",
            "subject_format": "[{company_name}] {year_month_display} 급여명세서입니다.",
            "from_address": "",
            "cc_list": [], "bcc_list": [],
            "include_password_hint_in_email": True,
            "password_hint_text": "첨부된 PDF 파일의 비밀번호는 귀하의 생년월일 8자리(YYYYMMDD)입니다.",
            "test_mode_recipient": "",
            "retry_attempts": 3,
            "retry_delay_seconds": 60
        }
    }
    try:
        if os.path.exists(settings_file):
            with open(settings_file, 'r', encoding='utf-8') as f:
                loaded_settings = yaml.safe_load(f)
                if loaded_settings:
                    operation_logger.info(f"[INFO] 설정 파일 '{settings_file}' 로딩 완료.")
                    # 기본 설정에 로드된 설정을 병합 (깊은 병합 필요시 수정)
                    for key, value in loaded_settings.items():
                        if isinstance(value, dict) and key in default_settings and isinstance(default_settings[key], dict):
                            default_settings[key].update(value)
                        else:
                            default_settings[key] = value
                    return default_settings
                else:
                    operation_logger.warning(f"[WARNING] 설정 파일 '{settings_file}'이 비어있습니다. 기본 설정을 사용합니다.")
        else:
            operation_logger.warning(f"[WARNING] 설정 파일 '{settings_file}'을(를) 찾을 수 없습니다. 기본 설정을 사용합니다.")
    except yaml.YAMLError as e:
        operation_logger.error(f"[ERROR] 설정 파일 '{settings_file}' 파싱 중 YAML 오류: {e}. 기본 설정을 사용합니다.", exc_info=True)
    except Exception as e:
        operation_logger.error(f"[ERROR] 설정 파일 '{settings_file}' 로드 중 예기치 않은 오류: {e}. 기본 설정을 사용합니다.", exc_info=True)
    
    operation_logger.info(f"[INFO] 기본 설정 사용됨.")
    return default_settings

@app.command()
def process_attendance(
    file: Annotated[str, typer.Option(help="근태 데이터 파일 경로 (예: data/attendance.csv)")]
) -> None:
    # 내용은 이전과 동일 (생략)
    operation_logger.info(f"[INFO] 명령어 실행: process_attendance, 파일: {file}")
    audit_logger.info(f"AUDIT: 근태 처리 명령어 시작. 파일: {file}")
    print(f"근태 데이터 처리 시작: {file}")
    # 여기에 실제 로직 구현 (현재는 플레이스홀더)
    settings = load_settings()
    wt_calculator = WorkTimeCalculator(settings)
    results = wt_calculator.process_attendance_file(file)
    print(f"근태 데이터 처리 완료. 결과: {results}")
    operation_logger.info(f"[INFO] 근태 데이터 처리 완료.")
    audit_logger.info(f"AUDIT: 근태 처리 명령어 종료.")

@app.command()
def calculate(
    employee_id_input: Annotated[str, typer.Option(help="급여를 계산할 직원 ID (예: EMP001). 'all' 입력 시 해당 연월의 모든 요약 파일 대상.", case_sensitive=False)] = "all", 
    year_month_input: Annotated[str, typer.Option(help="급여 계산 대상 연월 (YYYY-MM 형식, 예: 2025-07)")] = datetime.datetime.now().strftime("%Y-%m")
) -> None:
    # 내용은 이전과 동일 (생략)
    operation_logger.info(f"[INFO] 명령어 실행: calculate, 직원 ID: {employee_id_input}, 대상 연월: {year_month_input}")
    audit_logger.info(f"AUDIT: 급여 계산 명령어 시작. 직원 ID: {employee_id_input}, 대상 연월: {year_month_input}")
    settings = load_settings()
    company_payroll_settings = settings.get("company_info", {})
    # 여기에 실제 로직 구현 (현재는 플레이스홀더)
    payroll_calculator = PayrollCalculator(company_payroll_settings)
    # 예시: work_time_result는 이전 단계에서 생성된 것으로 가정
    work_time_result_placeholder = {"summary": {"total_work_hours": 160}}
    result = payroll_calculator.calculate_monthly_payroll(employee_id_input, year_month_input, work_time_result_placeholder)
    
    payroll_output_dir = settings.get("output_settings", {}).get("payroll_output_dir", "output/payroll")
    os.makedirs(payroll_output_dir, exist_ok=True)
    output_filename = f"{employee_id_input}_{year_month_input.replace('-', '')}_payroll.json"
    output_path = os.path.join(payroll_output_dir, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=4)
    print(f"급여 계산 완료. 결과 파일: {output_path}")
    operation_logger.info(f"[INFO] 급여 계산 완료. 결과 파일: {output_path}")
    audit_logger.info(f"AUDIT: 급여 계산 명령어 종료.")


def format_year_month_display(year_month_iso: str) -> str:
    """YYYY-MM 형식의 문자열을 YYYY년 MM월 형식으로 변환합니다."""
    try:
        dt_obj = datetime.datetime.strptime(year_month_iso, "%Y-%m")
        return dt_obj.strftime("%Y년 %m월")
    except ValueError:
        return year_month_iso # 형식 변환 실패 시 원본 반환

@app.command()
def generate_payslips(
    year_month_input: Annotated[str, typer.Option(help="급여명세서 생성 대상 연월 (YYYY-MM 형식, 예: 2025-07)")],
    employee_id_input: Annotated[str, typer.Option(help="급여명세서를 생성할 직원 ID (예: EMP001). 'all' 입력 시 해당 연월의 모든 payroll 파일 대상.", case_sensitive=False)] = "all",
    output_dir_input: Annotated[str, typer.Option(help="(선택) PDF/HTML 급여명세서를 저장할 사용자 정의 디렉토리 경로.")] = None,
    html_output: Annotated[bool, typer.Option("--html", help="PDF 외에 HTML 중간 산출물도 함께 저장합니다.")] = False,
    encrypt_pdf_flag: Annotated[bool, typer.Option("--encrypt", help="생성되는 PDF 급여명세서를 암호화합니다.")] = False,
    email_payslips_flag: Annotated[bool, typer.Option("--email", help="생성된 PDF 급여명세서를 직원에게 이메일로 발송합니다.")] = False,
    email_template_input: Annotated[str, typer.Option(help="사용할 이메일 템플릿 파일명 (settings.yaml의 email.templates_dir 내 위치, 확장자 포함).")] = None, # 기본값은 settings.yaml에서 로드
    test_email_flag: Annotated[bool, typer.Option("--test-email", help="이메일 발송 테스트 모드를 활성화합니다.")] = False
) -> None:
    """지정된 직원의 특정 연월 또는 전체 직원의 급여 계산 결과(_payroll.json)를 바탕으로 PDF 및 HTML 급여명세서를 생성하고, 선택적으로 PDF를 암호화하며, 이메일로 발송합니다."""
    start_time = time.time()
    operation_logger.info(f"[INFO] 명령어 실행: generate-payslips, 직원 ID: {employee_id_input}, 대상 연월: {year_month_input}, HTML: {html_output}, 암호화: {encrypt_pdf_flag}, 이메일: {email_payslips_flag}, 테스트 이메일: {test_email_flag}")
    audit_logger.info(f"AUDIT: 급여명세서 생성/발송 명령어 시작. 직원 ID: {employee_id_input}, 연월: {year_month_input}, 암호화: {encrypt_pdf_flag}, 이메일: {email_payslips_flag}")

    success_count = 0
    failure_count = 0
    email_sent_count = 0
    email_failed_count = 0
    emp_id_pattern = re.compile(r"(.+?)_(\d{6})_payroll\.json$")

    try:
        settings = load_settings()
        company_info = settings.get("company_info", {})
        payslip_s = settings.get("payslip_settings", {})
        template_dir = payslip_s.get("html_template_dir", "/home/ubuntu/upload/templates") # HTML 명세서 템플릿 경로
        template_name = payslip_s.get("html_template_name", "payslip_template.html")
        calc_msg_missing = payslip_s.get("calculation_message_if_missing", "계산식 정보 없음")

        encryption_settings = settings.get("pdf_encryption", {})
        should_encrypt_pdf = encrypt_pdf_flag or encryption_settings.get("enabled_by_default", False)
        password_format_template = encryption_settings.get("password_format", "{birth_date_YYYYMMDD}")
        encryption_failure_warning_msg = encryption_settings.get("encryption_failure_warning", "경고: PDF 암호화 실패.")
        user_password_hint = encryption_settings.get("user_password_hint", "비밀번호는 생년월일 8자리입니다.")

        email_settings = settings.get("email", {})
        # CLI 옵션이 우선, 없으면 settings.yaml의 default_template_name 사용
        final_email_template_name = email_template_input or email_settings.get("default_template_name", "default_payslip_email.html")

        payroll_json_dir = settings.get("output_settings", {}).get("payroll_output_dir", "output/payroll")
        
        if output_dir_input:
            final_pdf_output_dir = output_dir_input
            final_html_output_dir = output_dir_input
        else:
            final_pdf_output_dir = settings.get("output_settings", {}).get("payslip_pdf_dir", "output/payslips")
            final_html_output_dir = settings.get("output_settings", {}).get("payslip_html_dir", "output/payslips")
        
        os.makedirs(final_pdf_output_dir,
(Content truncated due to size limit. Use line ranges to read in chunks)