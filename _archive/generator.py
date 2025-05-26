# /home/ubuntu/upload/payslip/generator.py
import os
import json
import logging
from weasyprint import HTML, CSS # Ensure CSS is imported if used, though not directly in this snippet
from weasyprint.fonts import FontConfiguration

from .template_loader import TemplateLoader
from .utils.formatter import format_currency, format_year_month_display, format_date_display, format_calculation_field

logger = logging.getLogger(__name__)

class PayslipGenerator:
    # Modified __init__ to accept all parameters passed from cli.py
    def __init__(self, company_info: dict, template_dir: str, template_name: str, calculation_message_if_missing: str, settings: dict):
        self.company_info = company_info
        self.settings = settings # Store the whole settings dictionary
        self.template_dir = template_dir
        self.template_name = template_name
        self.missing_calculation_message = calculation_message_if_missing
        self.template_loader = TemplateLoader(template_dir=self.template_dir, template_name=self.template_name)
        self.font_config = FontConfiguration()

    def _prepare_template_context(self, payroll_data: dict) -> dict:
        context = payroll_data.copy()
        context.update(self.company_info)

        context["year_month_display"] = format_year_month_display(payroll_data.get("year_month"))
        context["pay_period"] = context["year_month_display"]
        context["pay_date"] = format_date_display(payroll_data.get("pay_date"))
        context["employee_id"] = payroll_data.get("employee_id")

        pay_components_data = payroll_data.get("pay_components", {}) 
        earnings_data = pay_components_data.get("earnings", {})
        deductions_data = pay_components_data.get("deductions", {})

        context["earnings_taxable"] = [
            {
                "name": item.get("name"),
                "amount_formatted": format_currency(item.get("amount")),
                "note": format_calculation_field(item.get("calculation"), item.get("note"), self.missing_calculation_message)
            } for item in earnings_data.get("taxable_breakdown", [])
        ]
        context["earnings_non_taxable"] = [
            {
                "name": item.get("name"),
                "amount_formatted": format_currency(item.get("amount")),
                "note": format_calculation_field(item.get("calculation"), item.get("note"), self.missing_calculation_message)
            } for item in earnings_data.get("non_taxable_breakdown", [])
        ]
        context["total_taxable_earnings_formatted"] = format_currency(earnings_data.get("total_taxable_earnings"))
        context["total_non_taxable_earnings_formatted"] = format_currency(earnings_data.get("total_non_taxable_earnings"))
        context["gross_pay_formatted"] = format_currency(earnings_data.get("gross_pay"))

        context["deductions_social_insurance"] = [
            {
                "name": item.get("name"),
                "amount_formatted": format_currency(item.get("amount")),
                "note": format_calculation_field(item.get("calculation"), item.get("note"), self.missing_calculation_message)
            } for item in deductions_data.get("social_insurance_breakdown", [])
        ]
        context["deductions_taxes"] = [
            {
                "name": item.get("name"),
                "amount_formatted": format_currency(item.get("amount")),
                "note": format_calculation_field(item.get("calculation"), item.get("note"), self.missing_calculation_message)
            } for item in deductions_data.get("tax_breakdown", [])
        ]
        context["deductions_other"] = [
            {
                "name": item.get("name"),
                "amount_formatted": format_currency(item.get("amount")),
                "note": format_calculation_field(item.get("calculation"), item.get("note"), self.missing_calculation_message)
            } for item in deductions_data.get("other_deductions_breakdown", [])
        ]
        context["total_deductions_formatted"] = format_currency(deductions_data.get("total_deductions"))
        context["net_pay_formatted"] = format_currency(payroll_data.get("net_pay"))

        work_time_summary_data = payroll_data.get("work_time_summary", {})
        work_summary = work_time_summary_data.get("summary", {})
        
        context["total_work_days"] = work_summary.get("total_work_days", "N/A")
        context["total_work_hours"] = work_summary.get("total_normal_hours", "N/A") 
        context["total_overtime_hours"] = work_summary.get("total_overtime_hours", "N/A")
        context["total_night_hours"] = work_summary.get("total_night_hours", "N/A")
        
        current_total_holiday_hours = work_summary.get("total_holiday_hours", "N/A")
        note_holiday_hours = work_summary.get("note_holiday_hours")
        if note_holiday_hours:
            context["total_holiday_hours"] = f"{current_total_holiday_hours} ({note_holiday_hours})"
        else:
            context["total_holiday_hours"] = current_total_holiday_hours

        employee_id_for_log = payroll_data.get("employee_id", "UnknownEmployee")
        logger.debug(f"Template context prepared for {employee_id_for_log}")
        return context

    def generate_pdf(self, payroll_data: dict, output_pdf_path: str) -> tuple[bool, str | None]:
        """
        Generates PDF payslip from payroll_data.
        Returns (success_flag, error_message_or_None)
        """
        employee_id = payroll_data.get("employee_id", "UnknownEmpID")
        try:
            os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)

            context = self._prepare_template_context(payroll_data)
            html_content = self.template_loader.render_template(context)
            
            template_base_dir = os.path.dirname(self.template_loader.template_path)
            html_obj = HTML(string=html_content, base_url=template_base_dir) 
            html_obj.write_pdf(output_pdf_path, font_config=self.font_config)
            logger.info(f"PDF 급여명세서 생성 성공: {output_pdf_path}")
            return True, None

        except RuntimeError as e: 
            err_msg = f"템플릿 처리 중 오류 발생 ({employee_id}): {e}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg
        except Exception as e:
            err_msg = f"급여명세서 생성 중 알 수 없는 오류 ({employee_id}): {e}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg

    def generate_html(self, payroll_data: dict) -> str | None:
        """
        Generates HTML content for a payslip from payroll_data.
        Returns HTML string or None if an error occurs.
        """
        employee_id = payroll_data.get("employee_id", "UnknownEmpID")
        try:
            context = self._prepare_template_context(payroll_data)
            html_content = self.template_loader.render_template(context)
            logger.info(f"HTML 급여명세서 내용 생성 성공 (직원 ID: {employee_id})")
            return html_content
        except RuntimeError as e:
            logger.error(f"HTML 생성 중 템플릿 처리 오류 ({employee_id}): {e}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"HTML 생성 중 알 수 없는 오류 ({employee_id}): {e}", exc_info=True)
            return None

    def convert_html_to_pdf(self, html_file_path: str, pdf_file_path: str) -> tuple[bool, str | None]:
        """
        Converts an existing HTML file to a PDF file.
        Returns (success_flag, error_message_or_None)
        """
        try:
            os.makedirs(os.path.dirname(pdf_file_path), exist_ok=True)
            
            # Read HTML content from the file
            with open(html_file_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Determine base_url for resolving relative paths (e.g., for CSS, images)
            # Assuming HTML file and its assets are in the same directory or template_dir is relevant
            base_url = os.path.dirname(html_file_path) # Or self.template_dir if more appropriate
            
            html_obj = HTML(string=html_content, base_url=base_url)
            html_obj.write_pdf(pdf_file_path, font_config=self.font_config)
            logger.info(f"HTML 파일로부터 PDF 생성 성공: {pdf_file_path} (원본 HTML: {html_file_path})")
            return True, None
        except FileNotFoundError:
            err_msg = f"HTML 파일을 찾을 수 없습니다: {html_file_path}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg
        except Exception as e:
            err_msg = f"HTML 파일로부터 PDF 변환 중 오류 발생 ({html_file_path} -> {pdf_file_path}): {e}"
            logger.error(err_msg, exc_info=True)
            return False, err_msg


