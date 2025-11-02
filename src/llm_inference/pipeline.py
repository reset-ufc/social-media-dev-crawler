import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from s1_make_llm_input import main as run_1_s1
from s2_detect_misuse import process_code_case as process_s2_case
from s4_summarization import main as run_4_s4
from s5_merge_llm_results import main as run_5_s5
from s0_utils import hierarquical_code_anylisis, run_pipeline_code_analysis, judge_code_analysis, run_pipeline_judge, load_csv_data
from paths import PREPROCESSED_POSTS, CODE_ANALYSIS, CODE_JUDGEMENT
from s3_judge_model import process_judge_case as process_s3_case


def run_full_pipeline(limit=0):
    run_pipeline_code_analysis(
        input_file=PREPROCESSED_POSTS,
        output_file=CODE_ANALYSIS,
        prompt_template=hierarquical_code_anylisis(),
        process_case_func=process_s2_case,
        data_loader=load_csv_data,
        limit=limit,
        description='Analysing codes'
    )
    run_pipeline_judge(
        input_file=CODE_ANALYSIS,
        output_file=CODE_JUDGEMENT,
        prompt_template=judge_code_analysis(),
        process_case_func=process_s3_case,
        limit=limit,
        description='Judging analyses'
    )
    run_4_s4()
    run_5_s5()


if __name__ == '__main__':
    run_full_pipeline(limit=3)
