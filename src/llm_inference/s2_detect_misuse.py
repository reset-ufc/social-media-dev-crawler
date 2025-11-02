import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from paths import PREPROCESSED_POSTS, CODE_ANALYSIS
from llm_inference.s0_utils import hierarquical_code_anylisis, run_pipeline_code_analysis, load_csv_data
from llm_inference.s1_make_llm_input import code_analyze_string, get_post_metadata

def process_code_case(case):
    """Processes a case for code analysis."""
    post_id = case.get('id')
    site = case.get('site')
    if not post_id or not site:
        return None
    code_input = code_analyze_string(str(post_id), site)
    if not code_input:
        return None
        
    metadata_input = get_post_metadata(str(post_id), site)
    
    return {"codes": code_input, "post_metadata": metadata_input}

if __name__ == "__main__":
    run_pipeline_code_analysis(
        input_file=PREPROCESSED_POSTS,
        output_file=CODE_ANALYSIS,
        prompt_template=hierarquical_code_anylisis(),
        process_case_func=process_code_case,
        data_loader=load_csv_data, 
        limit=6, 
        description="Analysing codes"
    )
