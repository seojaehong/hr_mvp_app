# /home/ubuntu/upload/payslip/security.py
import logging
from PyPDF2 import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

def encrypt_pdf(input_path: str, output_path: str, password: str) -> bool:
    """
    Encrypts a PDF file using PyPDF2.

    Args:
        input_path: Path to the original PDF file.
        output_path: Path to save the encrypted PDF file.
        password: Password to use for encryption.

    Returns:
        True if encryption was successful, False otherwise.
    """
    try:
        reader = PdfReader(input_path)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)

        with open(output_path, "wb") as output_file:
            writer.write(output_file)
        
        logger.info(f"PDF 암호화 성공: 원본='{input_path}', 암호화 파일='{output_path}'")
        return True
    except FileNotFoundError:
        logger.error(f"PDF 암호화 실패: 원본 파일을 찾을 수 없습니다 - '{input_path}'")
        return False
    except Exception as e:
        logger.error(f"PDF 암호화 중 오류 발생 (원본: '{input_path}'): {e}", exc_info=True)
        return False

# Placeholder for password generation logic (to be implemented in Plan 003)
def generate_password(employee_data: dict, settings: dict) -> str:
    """
    Generates a password based on employee data and settings.
    Placeholder for now.
    """
    # Example: employee_id + birth_date (YYYYMMDD)
    # Actual logic will depend on settings.yaml configuration
    employee_id = employee_data.get("employee_id", "UnknownEmp")
    birth_date_str = employee_data.get("employee_details", {}).get("birth_date", "19000101").replace("-","")
    
    # This is a very basic placeholder, actual implementation will be more robust
    # and configurable via settings.yaml
    default_pattern = settings.get("payslip_settings", {}).get("encryption", {}).get("default_password_pattern", "{employee_id}_{birth_date}")
    
    if default_pattern == "{employee_id}_{birth_date}":
        return f"{employee_id}_{birth_date_str}"
    
    # Fallback or more complex pattern handling would go here
    return f"{employee_id}DefaultPassword"

