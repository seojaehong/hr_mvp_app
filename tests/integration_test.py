#!/usr/bin/env python3
"""
정책 시뮬레이터 통합 테스트 스크립트

이 스크립트는 정책 시뮬레이터의 전체 기능을 end-to-end로 테스트합니다.
"""

import os
import sys
import json
import logging
from pathlib import Path
import argparse
from datetime import datetime

# 상위 디렉토리를 모듈 검색 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from payslip.policy_simulator import PolicySimulator
from payslip.scenario_loader import ScenarioLoader
from payslip.policy_summary import generate_policy_summary, export_policy_summary_to_html
from payslip.compare_results import compare_worktime_outputs, export_comparison_to_html
from payslip.combination_runner import (
    run_simulations_on_combinations, 
    generate_heatmap, 
    generate_policy_combination_matrix,
    filter_valid_combinations,
    export_simulation_results_to_html,
    export_simulation_results_to_json
)
# PayslipGenerator 클래스 임포트로 변경
from payslip.payslip_generator import PayslipGenerator

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('integration_test.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_output_dir():
    """출력 디렉토리를 설정합니다."""
    output_dir = Path('output/integration_test')
    output_dir.mkdir(exist_ok=True, parents=True)
    
    # 타임스탬프 기반 하위 디렉토리 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = output_dir / f'run_{timestamp}'
    run_dir.mkdir(exist_ok=True)
    
    return run_dir

def load_yaml_file(file_path):
    """YAML 파일을 로드합니다."""
    import yaml
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"YAML 파일 로드 중 오류 발생: {e}")
        return None

def test_single_simulation(input_data_path, policy_set_path, output_dir):
    """단일 정책 시뮬레이션을 테스트합니다."""
    logger.info("단일 정책 시뮬레이션 테스트 시작")
    
    # 입력 데이터 로드
    input_data = load_yaml_file(input_data_path)
    if not input_data:
        logger.error("입력 데이터 로드 실패")
        return False
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 세트 로드
    policy_set = scenario_loader.load_policy_set(policy_set_path)
    if not policy_set:
        logger.error("정책 세트 로드 실패")
        return False
    
    # 시뮬레이터 초기화 및 실행
    simulator = PolicySimulator()
    result = simulator.simulate(input_data, policy_set)
    
    # 결과 저장
    result_file = output_dir / 'simulation_result.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 정책 요약 생성 및 저장
    policy_summary = generate_policy_summary(result)
    summary_file = output_dir / 'policy_summary.json'
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(policy_summary, f, ensure_ascii=False, indent=2)
    
    # HTML 요약 생성
    html_summary_file = output_dir / 'policy_summary.html'
    export_policy_summary_to_html(policy_summary, str(html_summary_file))
    
    logger.info(f"단일 정책 시뮬레이션 테스트 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return True

def test_policy_comparison(input_data_path, policy_set1_path, policy_set2_path, output_dir):
    """정책 비교를 테스트합니다."""
    logger.info("정책 비교 테스트 시작")
    
    # 입력 데이터 로드
    input_data = load_yaml_file(input_data_path)
    if not input_data:
        logger.error("입력 데이터 로드 실패")
        return False
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 세트 로드
    policy_set1 = scenario_loader.load_policy_set(policy_set1_path)
    policy_set2 = scenario_loader.load_policy_set(policy_set2_path)
    
    if not policy_set1 or not policy_set2:
        logger.error("정책 세트 로드 실패")
        return False
    
    # 시뮬레이터 초기화 및 실행
    simulator = PolicySimulator()
    result1 = simulator.simulate(input_data, policy_set1)
    result2 = simulator.simulate(input_data, policy_set2)
    
    # 결과 저장
    result1_file = output_dir / 'result1.json'
    result2_file = output_dir / 'result2.json'
    
    with open(result1_file, 'w', encoding='utf-8') as f:
        json.dump(result1, f, ensure_ascii=False, indent=2)
    
    with open(result2_file, 'w', encoding='utf-8') as f:
        json.dump(result2, f, ensure_ascii=False, indent=2)
    
    # 비교 결과 생성
    comparison = compare_worktime_outputs(result1, result2)
    
    # 비교 결과 저장
    comparison_file = output_dir / 'comparison.json'
    with open(comparison_file, 'w', encoding='utf-8') as f:
        json.dump(comparison, f, ensure_ascii=False, indent=2)
    
    # HTML 비교 결과 생성
    html_comparison_file = output_dir / 'comparison.html'
    export_comparison_to_html(comparison, str(html_comparison_file))
    
    logger.info(f"정책 비교 테스트 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return True

def test_combination_simulation(input_data_path, policy_options_path, output_dir):
    """정책 조합 시뮬레이션을 테스트합니다."""
    logger.info("정책 조합 시뮬레이션 테스트 시작")
    
    # 입력 데이터 로드
    input_data = load_yaml_file(input_data_path)
    if not input_data:
        logger.error("입력 데이터 로드 실패")
        return False
    
    # 정책 옵션 로드
    policy_options = load_yaml_file(policy_options_path)
    if not policy_options:
        logger.error("정책 옵션 로드 실패")
        return False
    
    # 정책 조합 생성
    combinations = generate_policy_combination_matrix(policy_options)
    
    # 유효한 조합만 필터링
    valid_combinations = filter_valid_combinations(combinations)
    
    logger.info(f"총 {len(combinations)}개 조합 중 {len(valid_combinations)}개 유효한 조합 생성됨")
    
    # 조합 정보 저장
    combinations_file = output_dir / 'policy_combinations.json'
    with open(combinations_file, 'w', encoding='utf-8') as f:
        json.dump(valid_combinations, f, ensure_ascii=False, indent=2)
    
    # 시뮬레이션 실행
    simulation_results = run_simulations_on_combinations(
        input_data, 
        valid_combinations[:3],  # 테스트를 위해 처음 3개만 사용
        max_workers=2
    )
    
    # 결과 저장
    results_file = output_dir / 'simulation_results.json'
    export_simulation_results_to_json(simulation_results, str(results_file))
    
    # 히트맵 데이터 생성
    heatmap_data = generate_heatmap(simulation_results)
    
    # 히트맵 데이터 저장
    heatmap_file = output_dir / 'heatmap_data.json'
    with open(heatmap_file, 'w', encoding='utf-8') as f:
        json.dump(heatmap_data, f, ensure_ascii=False, indent=2)
    
    # HTML 결과 생성
    html_results_file = output_dir / 'simulation_results.html'
    export_simulation_results_to_html(simulation_results, str(html_results_file))
    
    logger.info(f"정책 조합 시뮬레이션 테스트 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return True

def test_payslip_generation(input_data_path, policy_set_path, output_dir):
    """급여명세서 생성을 테스트합니다."""
    logger.info("급여명세서 생성 테스트 시작")
    
    # 입력 데이터 로드
    input_data = load_yaml_file(input_data_path)
    if not input_data:
        logger.error("입력 데이터 로드 실패")
        return False
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 세트 로드
    policy_set = scenario_loader.load_policy_set(policy_set_path)
    if not policy_set:
        logger.error("정책 세트 로드 실패")
        return False
    
    # 시뮬레이터 초기화 및 실행
    simulator = PolicySimulator()
    result = simulator.simulate(input_data, policy_set)
    
    # 명세서 데이터 구성
    payslip_data = {
        "employee": {
            "name": "홍길동",
            "id": "EMP001"
        },
        "year_month": "2025-05",
        "time_summary": result.get("time_summary", {}),
        "applied_policies": result.get("applied_policies", [])
    }
    
    # 명세서 데이터 저장
    payslip_file = output_dir / 'payslip_data.json'
    with open(payslip_file, 'w', encoding='utf-8') as f:
        json.dump(payslip_data, f, ensure_ascii=False, indent=2)
    
    # 명세서 HTML 생성
    html_file = output_dir / 'payslip.html'
    
    # HTML 템플릿
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>급여명세서</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1, h2 {{ color: #333; text-align: center; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .info {{ margin-bottom: 20px; }}
            .info table {{ width: 100%; }}
            .info td {{ padding: 5px; }}
            .summary {{ margin-bottom: 20px; }}
            .summary table {{ width: 100%; border-collapse: collapse; }}
            .summary th, .summary td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            .summary th {{ background-color: #f2f2f2; }}
            .footer {{ margin-top: 50px; text-align: center; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>급여명세서</h1>
            <p>{payslip_data["year_month"]}</p>
        </div>
        
        <div class="info">
            <table>
                <tr>
                    <td><strong>직원명:</strong> {payslip_data["employee"]["name"]}</td>
                    <td><strong>직원 ID:</strong> {payslip_data["employee"]["id"]}</td>
                </tr>
            </table>
        </div>
        
        <div class="summary">
            <h2>급여 내역</h2>
            <table>
                <tr>
                    <th>항목</th>
                    <th>금액</th>
                </tr>
                <tr>
                    <td>기본급</td>
                    <td>{payslip_data["time_summary"].get("base_pay", 0):,}원</td>
                </tr>
                <tr>
                    <td>연장근로수당</td>
                    <td>{payslip_data["time_summary"].get("overtime_pay", 0):,}원</td>
                </tr>
                <tr>
                    <td>야간근로수당</td>
                    <td>{payslip_data["time_summary"].get("night_pay", 0):,}원</td>
                </tr>
                <tr>
                    <td>휴일근로수당</td>
                    <td>{payslip_data["time_summary"].get("holiday_pay", 0):,}원</td>
                </tr>
                <tr>
                    <th>총 지급액</th>
                    <th>{payslip_data["time_summary"].get("total_pay", 0):,}원</th>
                </tr>
            </table>
        </div>
        
        <div class="summary">
            <h2>근무 내역</h2>
            <table>
                <tr>
                    <th>항목</th>
                    <th>시간/일수</th>
                </tr>
                <tr>
                    <td>총 근무일수</td>
                    <td>{payslip_data["time_summary"].get("work_days", 0)}일</td>
                </tr>
                <tr>
                    <td>총 근무시간</td>
                    <td>{payslip_data["time_summary"].get("total_hours", 0)}시간</td>
                </tr>
                <tr>
                    <td>정규 근무시간</td>
                    <td>{payslip_data["time_summary"].get("regular_hours", 0)}시간</td>
                </tr>
                <tr>
                    <td>연장 근무시간</td>
                    <td>{payslip_data["time_summary"].get("overtime_hours", 0)}시간</td>
                </tr>
                <tr>
                    <td>야간 근무시간</td>
                    <td>{payslip_data["time_summary"].get("night_hours", 0)}시간</td>
                </tr>
                <tr>
                    <td>휴일 근무시간</td>
                    <td>{payslip_data["time_summary"].get("holiday_hours", 0)}시간</td>
                </tr>
            </table>
        </div>
        
        <div class="footer">
            <p>본 명세서는 자동 생성되었습니다.</p>
            <p>생성일: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        </div>
    </body>
    </html>
    """
    
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # PDF 파일 생성 시도
    try:
        pdf_file = output_dir / 'payslip.pdf'
        
        # PayslipGenerator 클래스 인스턴스 생성 및 메서드 호출로 변경
        # 테스트용 기본 설정값 사용
        mock_company_info = {"company_name": "테스트 회사", "company_address": "서울시 강남구"}
        mock_template_dir = str(Path("/home/ubuntu/upload/templates").absolute())
        mock_template_name = "payslip_template.html"
        
        # PayslipGenerator 인스턴스 생성
        generator = PayslipGenerator(
            company_info=mock_company_info,
            template_dir=mock_template_dir,
            template_name=mock_template_name,
            calculation_message_if_missing="계산식이 제공되지 않았습니다."
        )
        
        # HTML 파일을 PDF로 변환
        success, error_msg = generator.convert_html_to_pdf(str(html_file), str(pdf_file))
        
        if success:
            logger.info(f"PDF 명세서가 {pdf_file}에 생성되었습니다.")
        else:
            logger.warning(f"PDF 생성 실패: {error_msg}")
            
    except Exception as e:
        logger.warning(f"PDF 생성 중 오류 발생: {e}")
    
    logger.info(f"급여명세서 생성 테스트 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return True

def run_all_tests():
    """모든 테스트를 실행합니다."""
    logger.info("통합 테스트 시작")
    
    # 출력 디렉토리 설정
    output_dir = setup_output_dir()
    logger.info(f"출력 디렉토리: {output_dir}")
    
    # 테스트 파일 경로
    input_data_path = "tests/fixtures/timecard_cases.yaml"
    policy_set_path = "tests/fixtures/policy_scenarios.yaml"
    policy_set2_path = "enhanced_policy_scenarios.yaml"
    policy_options_path = "enhanced_policy_scenarios_v2.yaml"
    
    # 테스트 디렉토리 생성
    single_sim_dir = output_dir / "single_simulation"
    comparison_dir = output_dir / "policy_comparison"
    combination_dir = output_dir / "combination_simulation"
    payslip_dir = output_dir / "payslip_generation"
    
    single_sim_dir.mkdir(exist_ok=True)
    comparison_dir.mkdir(exist_ok=True)
    combination_dir.mkdir(exist_ok=True)
    payslip_dir.mkdir(exist_ok=True)
    
    # 테스트 실행
    test_results = {
        "single_simulation": test_single_simulation(input_data_path, policy_set_path, single_sim_dir),
        "policy_comparison": test_policy_comparison(input_data_path, policy_set_path, policy_set2_path, comparison_dir),
        "combination_simulation": test_combination_simulation(input_data_path, policy_options_path, combination_dir),
        "payslip_generation": test_payslip_generation(input_data_path, policy_set_path, payslip_dir)
    }
    
    # 테스트 결과 요약
    logger.info("테스트 결과 요약:")
    for test_name, result in test_results.items():
        status = "성공" if result else "실패"
        logger.info(f"  {test_name}: {status}")
    
    # 전체 테스트 결과
    all_passed = all(test_results.values())
    if all_passed:
        logger.info("모든 테스트가 성공적으로 완료되었습니다.")
    else:
        logger.warning("일부 테스트가 실패했습니다.")
    
    # 결과 파일 생성
    summary_file = output_dir / "test_summary.json"
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "results": test_results,
            "all_passed": all_passed
        }, f, ensure_ascii=False, indent=2)
    
    logger.info(f"테스트 요약이 {summary_file}에 저장되었습니다.")
    
    return all_passed, output_dir

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='정책 시뮬레이터 통합 테스트')
    parser.add_argument('--output-dir', help='출력 디렉토리 경로')
    args = parser.parse_args()
    
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
    
    success, output_dir = run_all_tests()
    
    if success:
        print(f"모든 테스트가 성공적으로 완료되었습니다. 결과가 {output_dir}에 저장되었습니다.")
        sys.exit(0)
    else:
        print(f"일부 테스트가 실패했습니다. 자세한 내용은 로그를 확인하세요.")
        sys.exit(1)

if __name__ == "__main__":
    main()
