import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from paths import CODE_ANALYSIS, CODE_JUDGEMENT
from llm_inference.s0_utils import judge_code_analysis, run_pipeline_judge
from llm_inference.s1_make_llm_input import code_analyze_string


def process_judge_case(case):
    """Processes a case for the judging pipeline."""
    post_id = case.get('question_id')
    site = case.get('site', '')
    
    code_input = code_analyze_string(str(post_id), site)
    analysis_input = json.dumps(case, indent=2)

    return {"codes": code_input, "analysis": analysis_input}

if __name__ == "__main__":
    run_pipeline_judge(
        input_file=CODE_ANALYSIS,
        output_file=CODE_JUDGEMENT,
        prompt_template=judge_code_analysis(),
        process_case_func=process_judge_case,
        limit=3,
        description="Judging analyses"
    )
