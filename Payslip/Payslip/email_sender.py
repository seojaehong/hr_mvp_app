# Payslip/payslip/email_sender.py
import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)

class PayslipEmailSender:
    def __init__(self, smtp_settings: dict):
        """
        이메일 발송을 위한 SMTP 설정 초기화
        
        Args:
            smtp_settings: SMTP 서버 설정 (서버, 포트, 사용자, 비밀번호, TLS 사용 여부 등)
        """
        self.smtp_server = smtp_settings.get("server", "")
        self.smtp_port = smtp_settings.get("port", 587)
        self.use_tls = smtp_settings.get("use_tls", True)
        self.username = smtp_settings.get("username", "")
        self.password = smtp_settings.get("password", "")
        self.default_sender = smtp_settings.get("default_sender", "")
        
    def send_payslip(self, recipient_email: str, subject: str, body: str, 
                    pdf_attachment_path: str, sender_email: str = None) -> bool:
        """
        급여명세서 PDF를 첨부하여 이메일 발송
        
        Args:
            recipient_email: 수신자 이메일 주소
            subject: 이메일 제목
            body: 이메일 본문 (HTML 형식 가능)
            pdf_attachment_path: 첨부할 PDF 파일 경로
            sender_email: 발신자 이메일 (기본값 사용 시 None)
            
        Returns:
            bool: 발송 성공 여부
        """
        if not os.path.exists(pdf_attachment_path):
            logger.error(f"첨부할 PDF 파일이 존재하지 않습니다: {pdf_attachment_path}")
            return False
            
        try:
            # 이메일 메시지 생성
            msg = MIMEMultipart()
            msg['From'] = sender_email or self.default_sender
            msg['To'] = recipient_email
            msg['Subject'] = subject
            
            # 본문 추가
            msg.attach(MIMEText(body, 'html' if '<html>' in body.lower() else 'plain'))
            
            # PDF 첨부
            with open(pdf_attachment_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype='pdf')
                attachment.add_header('Content-Disposition', 'attachment', 
                                     filename=os.path.basename(pdf_attachment_path))
                msg.attach(attachment)
            
            # SMTP 서버 연결 및 이메일 발송
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.send_message(msg)
                
            logger.info(f"급여명세서 이메일 발송 성공: {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"급여명세서 이메일 발송 실패 ({recipient_email}): {e}", exc_info=True)
            return False
            
    def send_bulk_payslips(self, payslip_data_list: list) -> dict:
        """
        여러 직원에게 급여명세서 일괄 발송
        
        Args:
            payslip_data_list: 발송할 급여명세서 데이터 목록
                [
                    {
                        'recipient_email': '이메일 주소',
                        'subject': '이메일 제목',
                        'body': '이메일 본문',
                        'pdf_attachment_path': 'PDF 파일 경로'
                    },
                    ...
                ]
                
        Returns:
            dict: 발송 결과 요약 (성공 수, 실패 수, 실패 목록)
        """
        results = {
            'total': len(payslip_data_list),
            'success': 0,
            'failed': 0,
            'failed_list': []
        }
        
        for data in payslip_data_list:
            success = self.send_payslip(
                recipient_email=data.get('recipient_email', ''),
                subject=data.get('subject', ''),
                body=data.get('body', ''),
                pdf_attachment_path=data.get('pdf_attachment_path', ''),
                sender_email=data.get('sender_email', None)
            )
            
            if success:
                results['success'] += 1
            else:
                results['failed'] += 1
                results['failed_list'].append(data.get('recipient_email', ''))
                
        return results
