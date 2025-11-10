from s4_merge_llm_results import main as run_s4
from s3_summarization import main as run_s3
from s2_llm_chain import run_llm_chain, load_csv_data
from s1_make_llm_input import input_hierarquical_code_analysis, input_hierarquical_code_judgement
from s0_utils import load_prompt
from paths import *
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_full_pipeline(limit=0):
    run_llm_chain(
        input_file=PREPROCESSED_POSTS,
        output_file=HIER_LLM_CLASSIFICATION,
        prompt_template=load_prompt("code_analysis_v1.txt", 'h'),
        process_case_func=input_hierarquical_code_analysis,
        data_loader=load_csv_data,
        filter_dict={'type': 'question'},
        limit=limit,
        description='Analysing codes'
    )
    run_llm_chain(
        input_file=HIER_LLM_CLASSIFICATION,
        output_file=HIER_CODE_JUDGEMENT,
        prompt_template=load_prompt("code_judge_v1.txt", 'h'),
        process_case_func=input_hierarquical_code_judgement,
        limit=limit,
        description='Judging analyses'
    )
    run_s3()
    run_s4()


if __name__ == '__main__':
    run_full_pipeline(limit=3)
