        
        # 검증 (케이스 1)
        # 예상 결과: 8시간 - 지각 30분 = 7.5시간
        self.assertEqual(result_case1.time_summary.regular_hours, Decimal("7.50"))
        self.assertEqual(result_case1.time_summary.total_net_work_hours, Decimal("7.50"))
        
        # 케이스 2: 조퇴 30분
        records_case2 = [
            TimeCardRecord(date=datetime.date(2025, 5, 27), start_time="09:00", end_time="17:30", break_time_minutes=60)
        ]
        
        input_data_case2 = TimeCardInputData(
            employee_id="test_tardiness_early_leave_calculation_case2",
            period="2025-05",
            records=records_case2
        )
        
        # 계산 실행 (케이스 2)
        result_case2 = self.calculator.calculate(input_data_case2)
        
        # 검증 (케이스 2)
        # 예상 결과: 8시간 - 조퇴 30분 = 7.5시간
        self.assertEqual(result_case2.time_summary.regular_hours, Decimal("7.50"))
        self.assertEqual(result_case2.time_summary.total_net_work_hours, Decimal("7.50"))
        
        # 케이스 3: 지각 15분 + 조퇴 15분
        records_case3 = [
            TimeCardRecord(date=datetime.date(2025, 5, 28), start_time="09:15", end_time="17:45", break_time_minutes=60)
        ]
        
        input_data_case3 = TimeCardInputData(
            employee_id="test_tardiness_early_leave_calculation_case3",
            period="2025-05",
            records=records_case3
        )
        
        # 계산 실행 (케이스 3)
        result_case3 = self.calculator.calculate(input_data_case3)
        
        # 검증 (케이스 3)