import os

# 루트 경로
BASE_DIR = os.path.join(os.getcwd(), "Payslip")

# 수정할 경로 매핑
RENAME_MAP = {
    "from Payslip.work_time_schema": "from Payslip.Worktime.schema",
    "from Payslip.work_time_processor": "from Payslip.Worktime.processor",
    "from Payslip.attendance_calculator": "from Payslip.Worktime.attendance",
    "from Payslip.timecard_calculator": "from Payslip.Worktime.calculator",
    "from Payslip.work_time_module": "from Payslip.Worktime.work_time_module",
}

# .py 파일 전체 탐색
for root, _, files in os.walk(BASE_DIR):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated = content
            for old, new in RENAME_MAP.items():
                updated = updated.replace(old, new)

            if updated != content:
                print(f"🔧 수정됨: {file_path}")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated)
