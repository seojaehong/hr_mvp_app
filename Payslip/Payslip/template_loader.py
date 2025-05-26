# Payslip/Payslip/template_loader.py 수정
import os
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

class TemplateLoader:
    def __init__(self, template_dir=None, template_name="payslip_template.html"):
        """
        HTML 템플릿 로더 초기화
        
        Args:
            template_dir: 템플릿 디렉토리 경로 (기본값: 현재 디렉토리 기준 상대 경로)
            template_name: 템플릿 파일명
        """
        # 기본 템플릿 디렉토리 설정 - 로컬 환경에 맞게 수정
        if template_dir is None:
            # 현재 파일 위치 기준으로 상대 경로 계산
            curnt_dir = os.path.dirname(os.path.abspath(__file__))
            # 프로젝트 루트 디렉토리로 이동 후 Templates 폴더 참조
            template_dir = os.path.join(os.path.dirname(os.path.dirname(current_dir)), "Templates")
        
        self.template_dir = template_dir
        self.template_name = template_name
        self.template = None
        self._load_template()
        
    def _load_template(self):
        """템플릿 파일 로드"""
        try:
            logger.info(f"템플릿 디렉토리: {self.template_dir}")
            logger.info(f"템플릿 파일명: {self.template_name}")
            
            # 템플릿 파일 존재 확인
            template_path = os.path.join(self.template_dir, self.template_name)
            if not os.path.exists(template_path):
                logger.error(f"템플릿 파일이 존재하지 않습니다: {template_path}")
                raise FileNotFoundError(f"Template file not found: {template_path}")
            
            # Jinja2 환경 설정
            env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            
            # 템플릿 로드
            self.template = env.get_template(self.template_name)
            logger.info(f"템플릿 로드 성공: {self.template_name}")
            
        except FileNotFoundError as fnfe:
            logger.error(f"템플릿 파일 찾기 실패: {fnfe}")
            raise RuntimeError(f"템플릿 파일 찾기 실패: {fnfe}")
        except Exception as e:
            logger.error(f"템플릿 로드 중 오류 발생: {e}")
            raise RuntimeError(f"템플릿 로드 실패: {e}")
    
    def render(self, context):
        """
        템플릿 렌더링
        
        Args:
            context: 템플릿에 전달할 컨텍스트 데이터
            
        Returns:
            str: 렌더링된 HTML 문자열
        """
        if self.template is None:
            raise RuntimeError("템플릿이 로드되지 않았습니다.")
        
        try:
            return self.template.render(**context)
        except Exception as e:
            logger.error(f"템플릿 렌더링 중 오류 발생: {e}")
            raise RuntimeError(f"템플릿 렌더링 실패: {e}")
