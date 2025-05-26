#!/usr/bin/env python3
"""
정책 시뮬레이터 테스트 및 시각화 CLI

이 스크립트는 정책 시뮬레이터를 테스트하고 결과를 시각화하는 명령줄 인터페이스를 제공합니다.
"""

import argparse
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path

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
    export_simulation_results_to_html
)

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('policy_simulator_cli.log')
    ]
)

logger = logging.getLogger(__name__)

def setup_output_dir():
    """출력 디렉토리를 설정합니다."""
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # 타임스탬프 기반 하위 디렉토리 생성
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    run_dir = output_dir / f'run_{timestamp}'
    run_dir.mkdir(exist_ok=True)
    
    return run_dir

def load_input_data(input_file):
    """입력 데이터를 로드합니다."""
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"입력 파일 로드 중 오류 발생: {e}")
        sys.exit(1)

def run_single_simulation(args):
    """단일 정책 시뮬레이션을 실행합니다."""
    # 출력 디렉토리 설정
    output_dir = setup_output_dir()
    
    # 입력 데이터 로드
    input_data = load_input_data(args.input)
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 세트 로드
    policy_set = scenario_loader.load_policy_set(args.policy_set)
    
    # 시뮬레이터 초기화 및 실행
    simulator = PolicySimulator()
    result = simulator.simulate(input_data, policy_set)
    
    # 결과 저장
    result_file = output_dir / 'simulation_result.json'
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 정책 요약 생성 및 저장
    if args.summary:
        policy_summary = generate_policy_summary(result)
        summary_file = output_dir / 'policy_summary.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(policy_summary, f, ensure_ascii=False, indent=2)
        
        # HTML 요약 생성
        html_summary_file = output_dir / 'policy_summary.html'
        export_policy_summary_to_html(policy_summary, str(html_summary_file))
    
    logger.info(f"시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
    print(f"시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return result, output_dir

def run_comparison(args):
    """두 정책 간 비교를 실행합니다."""
    # 출력 디렉토리 설정
    output_dir = setup_output_dir()
    
    # 입력 데이터 로드
    input_data = load_input_data(args.input)
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 세트 로드
    policy_set1 = scenario_loader.load_policy_set(args.policy_set1)
    policy_set2 = scenario_loader.load_policy_set(args.policy_set2)
    
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
    
    logger.info(f"정책 비교 완료. 결과가 {output_dir}에 저장되었습니다.")
    print(f"정책 비교 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return comparison, output_dir

def run_combination_simulation(args):
    """정책 조합 시뮬레이션을 실행합니다."""
    # 출력 디렉토리 설정
    output_dir = setup_output_dir()
    
    # 입력 데이터 로드
    input_data = load_input_data(args.input)
    
    # 시나리오 로더 초기화
    scenario_loader = ScenarioLoader()
    
    # 정책 옵션 로드
    policy_options = scenario_loader.load_policy_options(args.options)
    
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
        valid_combinations,
        max_workers=args.workers
    )
    
    # 결과 저장
    results_file = output_dir / 'simulation_results.json'
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(simulation_results, f, ensure_ascii=False, indent=2)
    
    # 히트맵 데이터 생성
    heatmap_data = generate_heatmap(simulation_results)
    
    # 히트맵 데이터 저장
    heatmap_file = output_dir / 'heatmap_data.json'
    with open(heatmap_file, 'w', encoding='utf-8') as f:
        json.dump(heatmap_data, f, ensure_ascii=False, indent=2)
    
    # HTML 결과 생성
    html_results_file = output_dir / 'simulation_results.html'
    export_simulation_results_to_html(simulation_results, str(html_results_file))
    
    logger.info(f"조합 시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
    print(f"조합 시뮬레이션 완료. 결과가 {output_dir}에 저장되었습니다.")
    
    return simulation_results, output_dir

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='정책 시뮬레이터 CLI')
    subparsers = parser.add_subparsers(dest='command', help='명령')
    
    # 단일 시뮬레이션 명령
    simulate_parser = subparsers.add_parser('simulate', help='단일 정책 시뮬레이션 실행')
    simulate_parser.add_argument('--input', '-i', required=True, help='입력 데이터 파일 경로')
    simulate_parser.add_argument('--policy-set', '-p', required=True, help='정책 세트 파일 경로')
    simulate_parser.add_argument('--summary', '-s', action='store_true', help='정책 요약 생성 여부')
    
    # 비교 명령
    compare_parser = subparsers.add_parser('compare', help='두 정책 간 비교 실행')
    compare_parser.add_argument('--input', '-i', required=True, help='입력 데이터 파일 경로')
    compare_parser.add_argument('--policy-set1', '-p1', required=True, help='첫 번째 정책 세트 파일 경로')
    compare_parser.add_argument('--policy-set2', '-p2', required=True, help='두 번째 정책 세트 파일 경로')
    
    # 조합 시뮬레이션 명령
    combination_parser = subparsers.add_parser('combinations', help='정책 조합 시뮬레이션 실행')
    combination_parser.add_argument('--input', '-i', required=True, help='입력 데이터 파일 경로')
    combination_parser.add_argument('--options', '-o', required=True, help='정책 옵션 파일 경로')
    combination_parser.add_argument('--workers', '-w', type=int, default=4, help='병렬 처리 작업자 수')
    
    args = parser.parse_args()
    
    if args.command == 'simulate':
        run_single_simulation(args)
    elif args.command == 'compare':
        run_comparison(args)
    elif args.command == 'combinations':
        run_combination_simulation(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
