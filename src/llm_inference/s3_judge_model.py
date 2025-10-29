import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

from paths import MISUSE_CASES_CODES, JUDGEMENT_CODES
from llm_inference.s0_utils import *
from llm_inference.s1_make_llm_input import code_analyze_string


def process_judge_case(case):
    """Processes a case for the judging pipeline."""
    post_id = case.get('post_id')
    code_input = code_analyze_string(str(post_id))
    analysis_input = json.dumps(case, indent=2)
    return {"codes": code_input, "analysis": analysis_input}

if __name__ == "__main__":
    run_pipeline(
        input_file=MISUSE_CASES_CODES,
        output_file=JUDGEMENT_CODES,
        prompt_template=judge_code_analysis(),
        process_case_func=process_judge_case,
        id_column='post_id',
        limit=2,
        description="Judging analyses"
    )
    