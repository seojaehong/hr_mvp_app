# yslip/Payslip/generator.py
from __future__ import annotations # Python 3.7+ 에서 미래의 타입 힌트 문법을 사용 가능하게 함
import os
import json
import logging
from typing import Dict, List, Any, Optional, Union, Tuple # typing 모듈에서 필요한 타입들 임포트

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration


from .template_loader import TemplateLoader
from ..Utils.formatter import format_currency, format_year_month_display, format_date_display, format_calculation_field
# Import encryption utilities
from .security import encrypt_pdf, generate_password
# Import email sender
from .email_sender import PayslipEmailSender

logger = logging.getLogger(__name__)

class PayslipGenerator:
    def __init__(self, company_info: dict, settings: dict, tenant_id: str = None):
        self.company_info = company_info
        self.settings = settings
        self.tenant_id = tenant_id
        
        payslip_settings = self.settings.get("payslip_settings", {})
        
        template_dir = payslip_settings.get("html_template_dir") 
        if not template_dir or not os.path.isdir(template_dir):
            logger.error(f"HTML 템플릿 디렉토리를 찾을 수 없거나 유효하지 않습니다: {template_dir}. settings의 'payslip_settings.html_template_dir'를 확인하세요.")
            # 여기에 적절한 예외 처리 또는 기본값 설정을 추가할 수 있습니다.
            # 예: raise ValueError(f"Invalid template directory: {template_dir}")
            # 또는 self.template_loader = None 등으로 설정하고 다른 메소드에서 확인

        template_name = payslip_settings.get("html_template_name", "payslip_template.html")
        self.missing_calculation_message = payslip_settings.get("missing_calculation_message", "계산 정보 없음")
        
        # template_dir이 유효하지 않으면 TemplateLoader 생성 시 오류 발생 가능
        self.template_loader = TemplateLoader(template_dir=template_dir, template_name=template_name)
        self.font_config = FontConfiguration()
        
        email_settings = self.settings.get("email_settings", {})
        if email_settings and email_settings.get("server"):
            self.email_sender = PayslipEmailSender(email_settings)
        else:
            self.email_sender = None
            logger.info("이메일 설정이 제공되지 않았거나 완전하지 않아 이메일 발송 기능을 비활성화합니다.")

    def _prepare_template_context(self, payroll_data: dict, for_pdf: bool = True) -> Dict[str, Any]: # ✅ 반환 타입 명시
        context = {
            'company': self.company_info,
            'employee': payroll_data.get('employee_details', {}),
            'pay_period': format_year_month_display(payroll_data.get('year_month', '')),
            'pay_date': payroll_data.get('pay_date', self.company_info.get("default_pay_date", "지급일 정보 없음")),
            'earnings': payroll_data.get('earnings', []),
            'deductions': payroll_data.get('deductions', []),
            'summary': payroll_data.get('summary', {}),
            'format_currency': format_currency,
            'format_date_display': format_date_display,
            'format_calculation_field': format_calculation_field,
            'missing_calculation_message': self.missing_calculation_message,
            'tenant_id': self.tenant_id
        }
        for section_key in ['earnings', 'deductions']:
            for item in context.get(section_key, []):
                if 'amount' in item and isinstance(item['amount'], (int, float)):
                    item['amount_display'] = format_currency(item['amount'])
        
        if 'summary' in context:
            for key, value in context['summary'].items():
                if isinstance(value, (int, float)):
                    context['summary'][key] = format_currency(value)
        return context
        
    def generate_html(self, payroll_data: dict) -> str:
        context = self._prepare_template_context(payroll_data, for_pdf=False)
        try:
            html_content = self.template_loader.render(context)
            return html_content
        except Exception as e:
            logger.error(f"HTML 생성 중 오류 발생: {e}", exc_info=True)
            return f"<html><body>HTML 생성 중 오류가 발생했습니다: {e}</body></html>"

    def generate_pdf(self, payroll_data: dict, output_path: str) -> Tuple[bool, Optional[str]]: # ✅ 타입 힌트 수정
        html_content = self.generate_html(payroll_data)
        if "HTML 생성 중 오류가 발생했습니다" in html_content:
             return False, f"HTML 생성 실패로 PDF를 만들 수 없습니다. 오류: {html_content}"

        try:
            HTML(string=html_content, base_url=self.template_loader.template_dir).write_pdf(output_path, font_config=self.font_config)
            logger.info(f"PDF 생성 성공: {output_path}")
            return True, output_path
        except Exception as e:
            logger.error(f"PDF 생성 중 오류 발생 ({output_path}): {e}", exc_info=True)
            return False, str(e)

    # 사용자님이 제공해주신 코드 조각을 기반으로 한 generate_payslip 메소드
    def generate_payslip(self, payroll_data_path: str, output_dir: str,
                         save_html: bool = False, encrypt_pdf_flag: bool = False,
                         send_email: bool = False) -> Tuple[bool, Optional[str], Optional[str], Optional[Dict[str, Any]]]: # ✅ 타입 힌트 수정
        """
        급여 데이터를 기반으로 급여명세서 생성 및 이메일 발송
        
        Args:
            payroll_data_path: 급여 데이터 JSON 파일 경로
            output_dir: 출력 디렉토리
            save_html: HTML 파일 저장 여부
            encrypt_pdf_flag: PDF 암호화 여부
            send_email: 이메일 발송 여부
            
        Returns:
            tuple: (성공 여부, PDF 최종 경로, HTML 저장 경로, 이메일 발송 결과 상세)
        """
        final_pdf_path: Optional[str] = None # 타입 힌트 명시
        html_file_path: Optional[str] = None # 타입 힌트 명시
        email_send_result: Optional[Dict[str, Any]] = None # 타입 힌트 명시
        payroll_data: Optional[Dict[str, Any]] = None # 타입 힌트 명시

        try:
            # 1. 급여 데이터 로드
            if not os.path.exists(payroll_data_path):
                logger.error(f"급여 데이터 파일을 찾을 수 없습니다: {payroll_data_path}")
                return False, None, None, None
            with open(payroll_data_path, 'r', encoding='utf-8') as f:
                payroll_data = json.load(f)
            
            employee_id = payroll_data.get("employee_id", "UnknownEmpID")
            year_month_for_filename = payroll_data.get("year_month", "YYYYMM").replace("-", "")

            os.makedirs(output_dir, exist_ok=True)

            # 2. 원본 PDF 생성
            original_pdf_filename = f"{employee_id}_{year_month_for_filename}_payslip.pdf"
            original_pdf_path = os.path.join(output_dir, original_pdf_filename)
            
            # generate_pdf 호출은 사용자님이 제공한 코드 조각과 약간 다를 수 있음.
            # 여기서는 self.generate_pdf가 (bool, Optional[str])을 반환한다고 가정.
            pdf_creation_success, pdf_message_or_path = self.generate_pdf(payroll_data, original_pdf_path)
            
            if not pdf_creation_success:
                logger.error(f"원본 PDF 생성 실패 ({employee_id}): {pdf_message_or_path}")
                return False, original_pdf_path, None, None # 실패해도 original_pdf_path는 반환
            
            final_pdf_path = original_pdf_path

            # 3. HTML 파일 저장 (옵션)
            if save_html:
                html_content = self.generate_html(payroll_data)
                if "HTML 생성 중 오류가 발생했습니다" not in html_content:
                    html_filename = f"{employee_id}_{year_month_for_filename}_payslip.html"
                    html_file_path = os.path.join(output_dir, html_filename)
                    try:
                        with open(html_file_path, 'w', encoding='utf-8') as f:
                            f.write(html_content)
                        logger.info(f"HTML 파일 저장 성공: {html_file_path}")
                    except Exception as e:
                        logger.error(f"HTML 파일 저장 중 오류 발생 ({html_file_path}): {e}", exc_info=True)
                        html_file_path = None
                else:
                    logger.warning(f"HTML 내용 생성 실패로 HTML 파일을 저장하지 않습니다 ({employee_id}).")
            
            # 4. PDF 암호화 (옵션)
            if encrypt_pdf_flag and pdf_creation_success:
                employee_details = payroll_data.get("employee_details", {})
                birth_date_str = employee_details.get("birth_date", "").replace("-", "")
                employee_id_upper = employee_id.upper()

                # 설정 기반 패턴 로드
                encryption_config = self.settings.get("payslip_settings", {}).get("encryption", {})
                default_pattern = encryption_config.get("default_password_pattern", "{employee_id}_{birth_date}")

                # 패턴 기반 비밀번호 생성
                if birth_date_str:
                    password = default_pattern \
                        .replace("{employee_id}", employee_id_upper) \
                        .replace("{birth_date}", birth_date_str)
                else:
                    password = generate_password(employee_data=employee_details, settings=self.settings)

                encrypted_pdf_filename = f"{employee_id}_{year_month_for_filename}_payslip_encrypted.pdf"
                encrypted_pdf_path = os.path.join(output_dir, encrypted_pdf_filename)

                if encrypt_pdf(original_pdf_path, encrypted_pdf_path, password):
                    logger.info(f"PDF 암호화 성공: {encrypted_pdf_path}. 비밀번호: {password}")
                    final_pdf_path = encrypted_pdf_path
                else:
                    logger.warning(f"PDF 암호화 실패: {original_pdf_path}. 원본 PDF가 사용됩니다.")

            # 5. 이메일 발송 (옵션)
            if send_email and pdf_creation_success:
                if not self.email_sender:
                    logger.warning(f"Email sender가 초기화되지 않아 이메일을 발송할 수 없습니다 ({employee_id}).")
                    email_send_result = {'status': 'skipped', 'reason': 'email_sender_not_initialized'}
                else:
                    employee_email = payroll_data.get("employee_details", {}).get("email")
                    if not employee_email:
                        logger.warning(f"직원 ({employee_id})의 이메일 주소가 없어 발송할 수 없습니다.")
                        email_send_result = {'status': 'skipped', 'reason': 'no_recipient_email'}
                    else:
                        company_name = self.company_info.get("company_name", "회사")
                        year_month_display = format_year_month_display(payroll_data.get('year_month', ''))
                        employee_name = payroll_data.get("employee_details", {}).get("name", "직원")
                        
                        subject = f"[{company_name}] {year_month_display} 급여명세서 안내"
                        body = f"""
                        <html><body>
                        <p>안녕하세요, {employee_name}님.</p>
                        <p>{year_month_display} 급여명세서를 첨부 파일로 보내드립니다.</p>
                        """
                        if encrypt_pdf_flag:
                            body += "<p>첨부된 PDF 파일은 암호화되어 있습니다. 비밀번호는 [보안 정책에 따라 전달된 방법]으로 확인해주십시오.</p>"
                        body += f"""
                        <p>문의사항이 있으시면 담당자에게 연락주시기 바랍니다.</p>
                        <p>감사합니다.</p>
                        <p><strong>{company_name}</strong> 드림</p>
                        </body></html>
                        """

                        sent_successfully = self.email_sender.send_payslip(
                            recipient_email=employee_email,
                            subject=subject,
                            body=body,
                            pdf_attachment_path=final_pdf_path
                        )
                        if sent_successfully:
                            logger.info(f"급여명세서 이메일 발송 성공: {employee_id} ({employee_email})")
                            email_send_result = {'status': 'success', 'recipient': employee_email}
                        else:
                            logger.error(f"급여명세서 이메일 발송 실패: {employee_id} ({employee_email})")
                            email_send_result = {'status': 'failed', 'recipient': employee_email}
            elif send_email and not pdf_creation_success:
                logger.warning(f"PDF 생성 실패로 이메일을 발송하지 않습니다 ({employee_id}).")
                email_send_result = {'status': 'skipped', 'reason': 'pdf_creation_failed'}

            return True, final_pdf_path, html_file_path, email_send_result

        except Exception as e:
            logger.error(f"generate_payslip 중 예외 발생 (데이터 경로: {payroll_data_path}): {e}", exc_info=True)
            return False, final_pdf_path, html_file_path, email_send_result

    def generate_bulk_payslips(self, payroll_data_dir: str, output_dir: str,
                               save_html: bool = False, encrypt_pdf_flag: bool = False,
                               send_email: bool = False) -> Dict[str, Any]: # ✅ 타입 힌트 수정
        results = {
            'total_files_processed': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'generation_failed_list': [],
            'email_results': []
        }

        if not os.path.isdir(payroll_data_dir):
            logger.error(f"급여 데이터 디렉토리를 찾을 수 없습니다: {payroll_data_dir}")
            return results

        for filename in os.listdir(payroll_data_dir):
            if filename.endswith('_payroll.json'): 
                results['total_files_processed'] += 1
                payroll_data_path = os.path.join(payroll_data_dir, filename)
                
                logger.info(f"일괄 처리 중: {filename}")
                
                success, pdf_path, html_path, email_status = self.generate_payslip(
                    payroll_data_path=payroll_data_path,
                    output_dir=output_dir,
                    save_html=save_html,
                    encrypt_pdf_flag=encrypt_pdf_flag,
                    send_email=send_email
                )
                
                if success:
                    results['successful_generations'] += 1
                else:
                    results['failed_generations'] += 1
                    results['generation_failed_list'].append(filename)
                
                if email_status:
                    results['email_results'].append({
                        'file': filename,
                        'pdf_path': pdf_path,
                        'status_details': email_status
                    })
            
        logger.info(f"급여명세서 일괄 생성/발송 완료. 총 {results['total_files_processed']}건 처리, "
                    f"성공 {results['successful_generations']}건, 실패 {results['failed_generations']}건.")
        if send_email:
            successful_emails = sum(1 for res in results['email_results'] if res['status_details'] and res['status_details'].get('status') == 'success')
            logger.info(f"이메일 발송 시도 건 중 성공: {successful_emails}건")
            
        return results