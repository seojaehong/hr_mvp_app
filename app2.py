# app.py (임시 테스트용)
import streamlit as st
import sys

st.write("Attempting to import Payslip.work_time_schema...")
try:
    from Payslip import work_time_schema
    st.success("Successfully imported Payslip.work_time_schema!")

    # work_time_schema 모듈의 내용 일부를 출력해 볼 수 있습니다.
    st.write("Contents of work_time_schema (partial):")
    st.text(dir(work_time_schema)[:20]) # 처음 20개 속성/메서드 이름만

    # 추가로, work_time_processor도 시도해볼 수 있습니다.
    st.write("Attempting to import Payslip.work_time_processor...")
    from Payslip import work_time_processor
    st.success("Successfully imported Payslip.work_time_processor!")
    st.write("Contents of work_time_processor (partial):")
    st.text(dir(work_time_processor)[:20])

except ImportError as e:
    st.error(f"ImportError occurred: {e}")
    st.error(f"Traceback: {e.__traceback__}") # 좀 더 자세한 트레이스백
    st.write("Current sys.path:")
    st.write(sys.path)
except Exception as e:
    st.error(f"An unexpected error occurred: {e}")
    st.error(f"Traceback: {e.__traceback__}")
    st.write("Current sys.path:")
    st.write(sys.path)

# 다른 모든 원래 app.py 코드는 일단 주석 처리하거나 삭제합니다.