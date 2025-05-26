# Cli/payslip_cli.py
import os
import typer
import logging
from typing import Optional
import yaml

# 상대 경로 임포트를 위한 경로 설정
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Payslip.payslip.generator import PayslipGenerator

app = typer.Typer()
logger = logging.getLogger(__name__)

def load_settings(settings_path: str = "Config/settings.yaml"):
    """설정 파일 로드"""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
        return {}

def get_tenant_settings(settings: dict, tenant_id: Optional[str] = None):
    """테넌트별 설정 가져오기"""
    if not tenant_id:
        return settings.get("company_info", {}), settings
        
    tenants = settings.get("tenants", {})
    if tenant_id in tenants:
        # 테넌트별 설정과 기본 설정 병합
        tenant_settings = tenants[tenant_id]
        company_info = tenant_settings.copy()
        return company_info, settings
    else:
        logger.warning(f"테넌트 ID '{tenant_id}'에 대한 설정이 없습니다. 기본 설정을 사용합니다.")
        return settings.get("company_info", {}), settings

@app.command()
def generate_payslips(
    year_month: str = typer.Option(..., "--year-month", help="급여 연월 (YYYY-MM)"),
    employee_id: Optional[str] = typer.Option(None, "--employee-id", help="직원 ID (미지정 시 전체 직원)"),
    tenant_id: Optional[str] = typer.Option(None, "--tenant-id", help="테넌트 ID (미지정 시 기본 설정 사용)"),
    output_dir: Optional[str] = typer.Option(None, "--output-dir", help="출력 디렉토리 (미지정 시 기본 설정 사용)"),
    html: bool = typer.Option(False, "--html", help="HTML 파일도 생성"),
    encrypt: bool = typer.Option(False, "--encrypt", help="PDF 암호화"),
    email: bool = typer.Option(False, "--email", help="이메일 발송"),
    settings_path: str = typer.Option("Config/settings.yaml", "--settings", help="설정 파일 경로")
):
    """급여명세서 생성 및 발송"""
    try:
        # 설정 로드
        settings = load_settings(settings_path)
        company_info, settings = get_tenant_settings(settings, tenant_id)
        
        # 출력 디렉토리 설정
        if not output_dir:
            output_dir = settings.get("output_settings", {}).get("payslip_pdf_dir", "output/payslips")
        os.makedirs(output_dir, exist_ok=True)
        
        # 급여 데이터 경로 설정
        payroll_dir = settings.get("output_settings", {}).get("json_output_dir", "output/json")
        
        # PayslipGenerator 인스턴스 생성
        generator = PayslipGenerator(company_info, settings, tenant_id)
        
        if employee_id:
            # 단일 직원 처리
            payroll_file = f"{employee_id}_{year_month.replace('-', '')}_payroll.json"
            payroll_path = os.path.join(payroll_dir, payroll_file)
            
            if not os.path.exists(payroll_path):
                logger.error(f"급여 데이터 파일을 찾을 수 없습니다: {payroll_path}")
                return
                
            success, pdf_path, html_path, email_result = generator.generate_payslip(
                payroll_data_path=payroll_path,
                output_dir=output_dir,
                save_html=html,
                encrypt_pdf_flag=encrypt,
                send_email=email
            )
            
            if success:
                logger.info(f"급여명세서 생성 성공: {pdf_path}")
                if email_result:
                    logger.info(f"급여명세서 이메일 발송 성공")
                elif email:
                    logger.warning(f"급여명세서 이메일 발송 실패")
            else:
                logger.error(f"급여명세서 생성 실패: {employee_id}")
        else:
            # 전체 직원 일괄 처리
            results = generator.generate_bulk_payslips(
                payroll_data_dir=payroll_dir,
                output_dir=output_dir,
                save_html=html,
                encrypt_pdf_flag=encrypt,
                send_email=email
            )
            
            logger.info(f"급여명세서 일괄 생성 결과: 총 {results['total']}건, "
                       f"성공 {results['success']}건, 실패 {results['failed']}건")
            
            if email:
                logger.info(f"이메일 발송 결과: 성공 {results['email_sent']}건, "
                           f"실패 {results['email_failed']}건")
                
    except Exception as e:
        logger.error(f"급여명세서 생성 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app()
