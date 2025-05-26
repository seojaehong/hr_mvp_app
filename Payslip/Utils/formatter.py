# /home/ubuntu/upload/payslip/utils/formatter.py
import datetime

def format_currency(value):
    if value is None:
        return "0"
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return str(value) # 숫자가 아니면 그대로 반환

def format_year_month_display(year_month_str):
    if not year_month_str or year_month_str == "YYYY-MM":
        return "해당없음"
    try:
        return datetime.datetime.strptime(year_month_str, "%Y-%m").strftime("%Y년 %m월")
    except ValueError:
        return year_month_str # 잘못된 형식이면 그대로 반환

def format_date_display(date_str):
    if not date_str or date_str == "YYYY-MM-DD":
        return "해당없음"
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%Y년 %m월 %d일")
    except ValueError:
        return date_str # 잘못된 형식이면 그대로 반환

def format_calculation_field(calculation, note, missing_message="계산 정보 없음"):
    """
    급여 항목의 계산식 또는 비고를 포맷합니다.
    - calculation과 note가 모두 있으면: "{calculation} (참고: {note})"
    - calculation만 있으면: "{calculation}"
    - note만 있고 calculation이 없으면: "{missing_message} (참고: {note})"
    - 둘 다 없으면: "{missing_message}"
    """
    calc_present = calculation and str(calculation).strip()
    note_present = note and str(note).strip()

    if calc_present:
        if note_present:
            return f"{str(calculation).strip()} (참고: {str(note).strip()})"
        else:
            return str(calculation).strip()
    else:
        if note_present:
            # PM 요청: 계산식 누락 시 메시지 커스터마이징 가능하게 (settings.yaml 연동은 추후 PayslipGenerator에서 처리)
            return f"{missing_message} (참고: {str(note).strip()})"
        else:
            return missing_message

