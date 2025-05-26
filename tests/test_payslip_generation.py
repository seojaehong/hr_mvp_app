# tets/test_payslip_generation.py
import os
import sys
import logging
import json

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_settings(settings_path="Config/settings.yaml"):
    """설정 파일 로드"""
    try:
        import yaml
        with open(settings_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {e}")
        return {}

def test_payslip_generation():
    """급여명세서 생성 테스트"""
    try:
        # 1. 설정 로드
        settings = load_settings()
        if not settings:
            logger.error("설정 로드 실패, 테스트를 중단합니다.")
            return
            
        # 2. 테스트할 직원 ID와 연월 설정
        employee_id = "EMP001"
        year_month = "2025-07"
        
        # 3. 급여 데이터 파일 경로 확인
        payroll_dir = settings.get("output_settings", {}).get("json_output_dir", "output/json")
        payroll_file = f"{employee_id}_{year_month.replace('-', '')}_payroll.json"
        payroll_path = os.path.join(payroll_dir, payroll_file)

        if not os.path.exists(payroll_path):
            logger.error(f"급여 데이터 파일이 존재하지 않습니다: {payroll_path}")
            return
            
        logger.info(f"급여 데이터 파일 확인: {payroll_path}")
        
        # 4. PayslipGenerator 인스턴스 생성 및 명세서 생성
        from Payslip.Payslip.generator import PayslipGenerator
        
      # PayslipGenerator 인스턴스 생성 시 템플릿 경로 명시
        company_info = settings.get("company_info", {})
        output_dir = settings.get("output_settings", {}).get("payslip_pdf_dir", "output/payslips")
        os.makedirs(output_dir, exist_ok=True)
        
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Templates")
        settings["payslip_settings"] = settings.get("payslip_settings", {})
        settings["payslip_settings"]["html_template_dir"] = template_dir
        settings["payslip_settings"]["html_template_name"] = "payslip_template.html"

        generator = PayslipGenerator(company_info, settings)
        
        logger.info("급여명세서 생성 시작...")
        success, pdf_path, html_path, _ = generator.generate_payslip(
            payroll_data_path=payroll_path,
            output_dir=output_dir,
            save_html=True,
            encrypt_pdf_flag=True,
            send_email=False
        )
        
        # 5. 결과 확인
        if success:
            logger.info(f"급여명세서 생성 성공: PDF={pdf_path}, HTML={html_path}")
            
            if os.path.exists(pdf_path):
                logger.info(f"PDF 파일 크기: {os.path.getsize(pdf_path)} 바이트")
            else:
                logger.error(f"PDF 파일이 생성되지 않았습니다.")
                
            if html_path and os.path.exists(html_path):
                logger.info(f"HTML 파일 크기: {os.path.getsize(html_path)} 바이트")
        else:
            logger.error("급여명세서 생성 실패")
            
    except Exception as e:
        logger.error(f"테스트 중 오류 발생: {e}", exc_info=True)

if __name__ == "__main__":
    test_payslip_generation()
