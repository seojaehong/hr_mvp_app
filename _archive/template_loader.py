# /home/ubuntu/upload/payslip/template_loader.py
from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
import logging

logger = logging.getLogger(__name__)

class TemplateLoader:
    def __init__(self, template_dir: str, template_name: str):
        self.template_dir = os.path.abspath(template_dir) # Ensure absolute path
        self.template_name = template_name
        # Define template_path attribute here
        self.template_path = os.path.join(self.template_dir, self.template_name)
        self.env = None
        self.template = None
        self._load_template()

    def _load_template(self):
        try:
            # Check if the template file actually exists before trying to load
            if not os.path.isfile(self.template_path):
                logger.error(f"Template file not found at specified path: {self.template_path}")
                raise FileNotFoundError(f"Template file not found: {self.template_path}")

            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(["html", "xml"]),
                enable_async=False # WeasyPrint is synchronous
            )
            self.template = self.env.get_template(self.template_name)
            logger.info(f"HTML 템플릿 로드 성공: {self.template_path}")
        except FileNotFoundError as fnfe: # Catch the specific FileNotFoundError raised above
            # Log already done, re-raise to be caught by the CLI or calling module
            raise RuntimeError(f"템플릿 파일 찾기 실패: {fnfe}")
        except Exception as e:
            logger.error(f"Jinja2 템플릿 로딩 실패: {self.template_path} - {e}", exc_info=True)
            # Re-raise the exception to be caught by the CLI or calling module
            raise RuntimeError(f"템플릿 로딩에 실패했습니다: {e}")

    def render_template(self, context: dict) -> str:
        if not self.template:
            logger.error("템플릿이 로드되지 않아 렌더링할 수 없습니다.")
            raise RuntimeError("템플릿이 로드되지 않았습니다.")
        try:
            html_content = self.template.render(context)
            logger.debug("HTML 템플릿 렌더링 성공")
            return html_content
        except Exception as e:
            logger.error(f"HTML 템플릿 렌더링 중 오류 발생: {e}", exc_info=True)
            raise RuntimeError(f"템플릿 렌더링 중 오류가 발생했습니다: {e}")

