# tests/test_pdf_encryption.py
import os
import sys
import logging # 예시, 실제 사용하는 테스트 프레임워크에 따라 다를 수 있음

# --- sys.path 설정 추가 ---
# 현재 파일(test_pdf_encryption.py)의 디렉토리 (tests/)
current_dir = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 루트 디렉토리 (HR MVP Status and Context Inheritance (4)/)
project_root = os.path.dirname(current_dir)

# 프로젝트 루트를 sys.path에 추가
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- sys.path 설정 완료 ---

# 이제 Payslip 패키지 및 하위 모듈을 정상적으로 임포트할 수 있습니다.
from Payslip.Payslip.security import encrypt_pdf, generate_password

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_encrypt_pdf():
    # 테스트할 PDF 파일 경로
    input_pdf = "output/payslips/EMP001_202507_payslip.pdf"
    output_pdf = "output/payslips/EMP001_202507_payslip_encrypted.pdf"
    
    # 테스트용 직원 데이터
    employee_data = {
        "employee_id": "EMP001",
        "employee_details": {
            "birth_date": "1990-01-01"
        }
    }
    
    # 테스트용 설정
    settings = {
        "payslip_settings": {
            "encryption": {
                "default_password_pattern": "{employee_id}_{birth_date}"
            }
        }
    }
    
    # 암호 생성
    password = generate_password(employee_data, settings)
    logger.info(f"생성된 암호: {password}")
    
    # PDF 암호화
    if os.path.exists(input_pdf):
        result = encrypt_pdf(input_pdf, output_pdf, password)
        if result:
            logger.info(f"PDF 암호화 성공: {output_pdf}")
        else:
            logger.error("PDF 암호화 실패")
    else:
        logger.error(f"입력 PDF 파일이 존재하지 않습니다: {input_pdf}")

if __name__ == "__main__":
    test_encrypt_pdf()
