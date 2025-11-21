import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from paths import *
from s0_utils import *
from s1_make_llm_input import *
from s2_llm_chain import run_llm_chain, load_csv_questions
from s3_summarization import main as run_s3
from s4_merge_llm_results import main as run_s4



model = 'deepseek-r1:70b'


def flat_pipeline(limit=0):
    run_llm_chain(
        input_file=PREPROCESSED_POSTS,
        output_file=FLAT_CODE_ANALYSIS,
        prompt_template=load_prompt("code_analysis_v1.txt", 'f'),
        process_case_func=input_analyze_all_codes,
        data_loader=load_csv_questions,
        filter_dict={'type': 'question'},
        limit=limit,
        description='Analysing codes (flat)'
    )
    run_llm_chain(
        input_file=FLAT_CODE_ANALYSIS,
        output_file=FLAT_CODE_JUDGEMENT,
        prompt_template=load_prompt("code_judge_v1.txt", 'f'),
        process_case_func=input_judgement_all_codes,
        limit=limit,
        description='Judging analyses (flat)'
    )
    run_s3(FLAT_CODE_ANALYSIS, FLAT_CODE_ANALYSIS_SUMMARY)
    run_s4(FLAT_CODE_ANALYSIS, FLAT_CODE_JUDGEMENT,
           FLAT_MERGED_SUMMARY, FLAT_MERGED_LLM_RESULTS)


def hier_pipeline(limit=0):
    run_llm_chain(
        input_file=PREPROCESSED_POSTS,
        output_file=HIER_CODE_DETECTION,
        prompt_template=load_prompt("code_detection.txt", 'h'),
        process_case_func=input_analyze_all_codes,
        data_loader=load_csv_questions,
        filter_dict={'type': 'question'},
        limit=limit,
        description='Detecting (hier)',
        model_name=model,
    )
    run_llm_chain(
        input_file=HIER_CODE_DETECTION,
        output_file=HIER_CODE_TYPE,
        prompt_template=load_prompt("code_type.txt", 'h'),
        process_case_func=input_analysis_specific_codes,
        filter_dict={'has_misuse': True},
        limit=limit,
        description='Infering type (hier)',
        model_name=model,
    )
    combine_hier_codes(
        detection_path=HIER_CODE_DETECTION,
        code_type_path=HIER_CODE_TYPE,
        output_path=HIER_CODE_FULL_CLASSIFICATION
    )
    run_llm_chain(
        input_file=HIER_CODE_FULL_CLASSIFICATION,
        output_file=HIER_CODE_JUDGEMENT,
        prompt_template=load_prompt("code_judge_v2.txt", 'h'),
        process_case_func=input_judgement_all_codes,
        limit=limit,
        description='Judging analyses (hier)'
    )
    run_s3(HIER_CODE_FULL_CLASSIFICATION, HIER_CODE_ANALYSIS_SUMMARY)
    run_s4(HIER_CODE_FULL_CLASSIFICATION, HIER_CODE_JUDGEMENT,
           HIER_MERGED_SUMMARY, HIER_MERGED_LLM_RESULTS)


if __name__ == '__main__':
    hier_pipeline(limit=50)
