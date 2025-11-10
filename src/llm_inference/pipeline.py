from s4_merge_llm_results import main as run_s4
from s3_summarization import main as run_s3
from s2_llm_chain import run_llm_chain, load_csv_data
from s1_make_llm_input import input_flat_code_analysis, input_flat_code_judgement
from s0_utils import load_prompt
from paths import *
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def flat_pipeline(limit=0):
    run_llm_chain(
        input_file=PREPROCESSED_POSTS,
        output_file=FLAT_CODE_ANALYSIS,
        prompt_template=load_prompt("code_analysis_v1.txt", 'f'),
        process_case_func=input_flat_code_analysis,
        data_loader=load_csv_data,
        filter_dict={'type': 'question'},
        limit=limit,
        description='Analysing codes (flat)'
    )
    run_llm_chain(
        input_file=FLAT_CODE_ANALYSIS,
        output_file=FLAT_CODE_JUDGEMENT,
        prompt_template=load_prompt("code_judge_v1.txt", 'f'),
        process_case_func=input_flat_code_judgement,
        limit=limit,
        description='Judging analyses (flat)'
    )
    run_s3(FLAT_CODE_ANALYSIS, FLAT_CODE_ANALYSIS_SUMMARY)
    run_s4(FLAT_CODE_ANALYSIS, FLAT_CODE_JUDGEMENT, FLAT_MERGE_SUMMARY, FLAT_MERGED_LLM_RESULTS)


def hier_pipeline(limit=0):
    run_llm_chain(
        input_file=PREPROCESSED_POSTS,
        output_file=HIER_CODE_DETECTION,
        prompt_template=load_prompt("code_analysis_v1.txt", 'f'),
        process_case_func=input_flat_code_analysis,
        data_loader=load_csv_data,
        filter_dict={'type': 'question'},
        limit=limit,
        description='Detecting (hier)'
    )
    run_llm_chain(
        input_file=HIER_CODE_DETECTION,
        output_file=HIER_CODE_TYPE,
        prompt_template=load_prompt("code_judge_v1.txt", 'f'),
        process_case_func=input_flat_code_judgement,
        limit=limit,
        description='Infering type (hier)'
    )
    run_llm_chain(
        input_file=HIER_CODE_FULL_CLASSIFICATION,
        output_file=FLAT_CODE_JUDGEMENT,
        prompt_template=load_prompt("code_judge_v1.txt", 'f'),
        process_case_func=input_flat_code_judgement,
        limit=limit,
        description='Judging analyses (hier)'
    )
    run_s3()
    run_s4()


if __name__ == '__main__':
    flat_pipeline(limit=2)
